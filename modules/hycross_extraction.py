"""Module for reading and processing FLO-2D HYCROSS.OUT files."""

import os
import re
import pandas as pd
from typing import Dict, Tuple, List, Optional
import geopandas as gpd
from shapely.geometry import LineString
import logging


def _extract_hydrograph_data(file_path: str) -> Tuple[Dict[int, pd.DataFrame], Dict[int, float]]:
    """Extracts hydrograph data and maximum WSE from the HYCROSS.OUT file.
    
    Args:
        file_path (str): Path to the HYCROSS.OUT file
        
    Returns:
        Tuple containing:
            Dict[int, pd.DataFrame]: Time series data for each cross section
            Dict[int, float]: Maximum WSE for each cross section
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    hydrograph_data = {}
    max_discharge_info = {}
    max_wse_info = {}
    current_section = None
    current_wse = -float('inf')
    header_found = False

    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                    
                # Extract max discharge info
                if 'THE MAXIMUM DISCHARGE FROM CROSS SECTION' in line:
                    match = re.search(r'THE MAXIMUM DISCHARGE FROM CROSS SECTION\s*(\d+) IS:\s*([\d.]+) CFS AT TIME:\s*([\d.]+)', line)
                    if match:
                        section = int(match.group(1))
                        max_discharge = float(match.group(2))
                        max_time = float(match.group(3))
                        max_discharge_info[section] = (max_time, max_discharge)
                        logger.debug(f"Found max discharge for section {section}: {max_discharge} CFS at {max_time} hours")
                    continue

                # Extract max WSE info
                if 'MAXIMUM WATER SURFACE ELEVATION AT CROSS SECTION' in line:
                    match = re.search(r'MAXIMUM WATER SURFACE ELEVATION AT CROSS SECTION\s*(\d+)\s*IS:\s*([\d.]+)', line)
                    if match:
                        section = int(match.group(1))
                        max_wse = float(match.group(2))
                        max_wse_info[section] = max_wse
                        logger.debug(f"Found max WSE for section {section}: {max_wse}")
                    continue

                # Identify start of new section
                if 'HYDROGRAPH AND FLOODPLAIN HYDRAULICS' in line:
                    match = re.search(r'FOR CROSS SECTION NO:\s*(\d+)', line)
                    if match:
                        current_section = int(match.group(1))
                        hydrograph_data[current_section] = []
                        current_wse = -float('inf')
                        header_found = False
                        logger.debug(f"Processing cross section {current_section}")
                    continue

                # Skip header line but mark it as found
                if 'TIME' in line and 'DISCHARGE' in line:
                    header_found = True
                    continue

                # Extract time series data only if we've found a header
                if current_section is not None and header_found:
                    try:
                        parts = line.split()
                        if len(parts) >= 6:  # Ensure we have all required fields
                            time = float(parts[0])
                            flow_width = float(parts[1])
                            ave_depth = float(parts[2])
                            wse = float(parts[3])
                            velocity = float(parts[4])
                            discharge = float(parts[5])
                            
                            hydrograph_data[current_section].append(
                                (time, flow_width, ave_depth, wse, velocity, discharge)
                            )
                            
                            if wse > current_wse:
                                current_wse = wse
                                max_wse_info[current_section] = current_wse
                    except (IndexError, ValueError) as e:
                        logger.debug(f"Skipping invalid line in section {current_section}: {line.strip()} ({str(e)})")
                        continue

        # Convert to DataFrames and integrate max discharge
        processed_data = {}
        for section in hydrograph_data:
            if hydrograph_data[section]:  # Only process if we have data
                try:
                    df = pd.DataFrame(
                        hydrograph_data[section], 
                        columns=['Time', 'Flow_Width', 'Ave_Depth', 'WSE', 'Velocity', 'Discharge']
                    )
                    if section in max_discharge_info:
                        df = _integrate_max_discharge(df, max_discharge_info[section])
                    processed_data[section] = df
                    logger.debug(f"Processed {len(df)} rows for section {section}")
                except Exception as e:
                    logger.warning(f"Could not process data for section {section}: {str(e)}")
                    continue
                    
        if not processed_data:
            logger.warning("No valid cross section data found in HYCROSS.OUT")
            
        return processed_data, max_wse_info
        
    except Exception as e:
        logger.error(f"Error processing HYCROSS.OUT: {str(e)}")
        return {}, {}

def _integrate_max_discharge(df: pd.DataFrame, max_discharge_info: Tuple[float, float]) -> pd.DataFrame:
    """Integrates maximum discharge into the time series at the correct position.
    
    Args:
        df (pd.DataFrame): Time series DataFrame
        max_discharge_info (tuple): (max_time, max_discharge) tuple
        
    Returns:
        pd.DataFrame: Updated DataFrame with integrated max discharge
    """
    max_time, max_discharge = max_discharge_info

    if max_time in df['Time'].values:
        df.loc[df['Time'] == max_time, 'Discharge'] = max_discharge
    else:
        new_row = pd.DataFrame({'Time': [max_time], 'Discharge': [max_discharge]})
        df = pd.concat([df, new_row], ignore_index=True)
        df = df.sort_values(by='Time').reset_index(drop=True)

    return df

def _create_summary_df(hydrograph_data: Dict[int, pd.DataFrame], 
                      max_wse_info: Dict[int, float]) -> pd.DataFrame:
    """Creates summary DataFrame with maximum values for each cross section.
    
    Args:
        hydrograph_data (Dict[int, pd.DataFrame]): Time series data
        max_wse_info (Dict[int, float]): Maximum WSE values
        
    Returns:
        pd.DataFrame: Summary DataFrame with max values
    """
    summary_data = []
    
    if not hydrograph_data:
        return pd.DataFrame()  # Return empty DataFrame if no data
    
    for section, df in hydrograph_data.items():
        try:
            if df.empty:
                continue
                
            max_q = df['Discharge'].max() if 'Discharge' in df.columns else None
            time_to_peak = df.loc[df['Discharge'].idxmax(), 'Time'] if 'Discharge' in df.columns and 'Time' in df.columns else None
            max_wse = max_wse_info.get(section, None)
            
            max_flow_width = df['Flow_Width'].max() if 'Flow_Width' in df.columns else None
            max_ave_depth = df['Ave_Depth'].max() if 'Ave_Depth' in df.columns else None
            max_velocity = df['Velocity'].max() if 'Velocity' in df.columns else None
            
            summary_data.append({
                'fpxs_id': section,
                'q_max': max_q,
                'time_to_peak': time_to_peak,
                'wse_max': max_wse,
                'flow_width_max': max_flow_width,
                'ave_depth_max': max_ave_depth,
                'velocity_max': max_velocity
            })
        except Exception as e:
            logger = logging.getLogger('FLO2D_Postprocessor')
            logger.warning(f"Could not process summary data for cross section {section}: {str(e)}")
            continue
    
    return pd.DataFrame(summary_data) if summary_data else pd.DataFrame()

def hycross_extract(file_path: str) -> Tuple[pd.DataFrame, Dict[int, pd.DataFrame]]:
    """Read and process the HYCROSS.OUT file.
    
    Args:
        file_path (str): Path to the HYCROSS.OUT file
        
    Returns:
        Tuple containing:
            pd.DataFrame: Summary results with maximum values
            Dict[int, pd.DataFrame]: Time series data for each cross section
            
    Raises:
        FileNotFoundError: If the specified file does not exist
        IOError: If there are issues reading the file
    """
    try:
        # Extract time series and WSE data
        hydrograph_data, max_wse_info = _extract_hydrograph_data(file_path)
        
        # Create summary DataFrame
        summary_df = _create_summary_df(hydrograph_data, max_wse_info)
        
        return summary_df, hydrograph_data
        
    except Exception as e:
        logger = logging.getLogger('FLO2D_Postprocessor')
        logger.error(f"Error extracting HYCROSS data: {str(e)}")
        return pd.DataFrame(), {}

def main():
    folder_path = r"R:\_anichols\Projects\_flo2d_postprocessor_tests\Detroit_Basin_Prop100y24h"
    file_path = os.path.join(folder_path, "HYCROSS.OUT")
    
    try:
        # Get both summary and time series data
        summary_df, time_series_data = hycross_extract(file_path)
        
        # Print summary information
        print("Summary Results:")
        print(summary_df.head())
        
        # Print time series for first cross section
        first_section = min(time_series_data.keys())
        print(f"\nTime Series Data for Cross Section {first_section}:")
        print(time_series_data[first_section].head())
        
    except Exception as e:
        print(f"Error processing HYCROSS.OUT: {str(e)}")

if __name__ == "__main__":
    main()
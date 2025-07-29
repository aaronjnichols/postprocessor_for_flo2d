"""
Module for extracting outflow hydrograph data from FLO-2D OUTNQ.OUT files.

This module provides functions to parse and extract outflow hydrograph time series
and summary statistics from FLO-2D model output files.
"""

# Standard library imports
import os
import re
import logging

# Third-party imports
import pandas as pd

# Local application imports
from core.constants import GRID_ID, TIME, MAX_Q, TIME_PEAK, DISCHARGE
from core.logger import setup_logger


def extract_outnq_summary(folder_path):
    """
    Extract summary statistics from OUTNQ.OUT file.
    
    Args:
        folder_path (str): Path to the directory containing OUTNQ.OUT file.
        
    Returns:
        pd.DataFrame: DataFrame with columns ['grid_id', 'max_q', 'time_peak'] containing
                     maximum discharge and time to peak for each outflow element.
                     Returns empty DataFrame on error.
                     
    Raises:
        FileNotFoundError: If OUTNQ.OUT file is not found.
    """
    logger = setup_logger('OUTNQ_OUT', level=logging.INFO)
    file_path = os.path.join(folder_path, 'OUTNQ.OUT')
    
    if not os.path.exists(file_path):
        logger.error(f"OUTNQ.OUT file not found at {file_path}")
        raise FileNotFoundError(f"OUTNQ.OUT file not found at {file_path}")
    
    try:
        with open(file_path, 'r', errors='ignore') as file:
            content = file.read()
            
        # Parse max Q data using regex
        max_q_pattern = r"THE MAX Q AT OUTFLOW ELEMENT:\s+(\d+)\s+IS:\s+([\d.]+)\s+CFS AT TIME:\s+([\d.]+)"
        max_q_matches = re.findall(max_q_pattern, content)
        
        if not max_q_matches:
            logger.warning(f"No maximum discharge data found in {file_path}")
            return pd.DataFrame(columns=[GRID_ID, MAX_Q, TIME_PEAK])
        
        # Build summary dataframe from regex matches
        summary_data = []
        for grid_id_str, max_q_str, time_str in max_q_matches:
            try:
                grid_id = int(grid_id_str)
                max_q = float(max_q_str)
                time_peak = float(time_str)
                summary_data.append({
                    GRID_ID: grid_id,
                    MAX_Q: max_q,
                    TIME_PEAK: time_peak
                })
            except ValueError as e:
                logger.warning(f"Could not parse max Q data: ID={grid_id_str}, Q={max_q_str}, T={time_str}. Error: {e}")
                continue
        
        if not summary_data:
            logger.warning(f"No valid maximum discharge data found in {file_path}")
            return pd.DataFrame(columns=[GRID_ID, MAX_Q, TIME_PEAK])
        
        summary_df = pd.DataFrame(summary_data)
        
        # Ensure proper data types
        summary_df[GRID_ID] = pd.to_numeric(summary_df[GRID_ID], errors='coerce').astype('Int64')
        summary_df[MAX_Q] = pd.to_numeric(summary_df[MAX_Q], errors='coerce')
        summary_df[TIME_PEAK] = pd.to_numeric(summary_df[TIME_PEAK], errors='coerce')
        
        logger.info(f"Successfully extracted {len(summary_df)} outflow summary records from OUTNQ.OUT")
        return summary_df
        
    except IOError as e:
        logger.error(f"Error reading OUTNQ.OUT file: {e}")
        return pd.DataFrame(columns=[GRID_ID, MAX_Q, TIME_PEAK])
    except Exception as e:
        logger.error(f"Unexpected error processing OUTNQ.OUT file: {e}", exc_info=True)
        return pd.DataFrame(columns=[GRID_ID, MAX_Q, TIME_PEAK])


def extract_outnq_time_series(folder_path):
    """
    Extract time series hydrograph data from OUTNQ.OUT file.
    
    Args:
        folder_path (str): Path to the directory containing OUTNQ.OUT file.
        
    Returns:
        pd.DataFrame: DataFrame with time as index and grid IDs as columns,
                     containing discharge values. Returns empty DataFrame on error.
                     
    Raises:
        FileNotFoundError: If OUTNQ.OUT file is not found.
    """
    logger = setup_logger('OUTNQ_OUT', level=logging.INFO)
    file_path = os.path.join(folder_path, 'OUTNQ.OUT')
    
    if not os.path.exists(file_path):
        logger.error(f"OUTNQ.OUT file not found at {file_path}")
        raise FileNotFoundError(f"OUTNQ.OUT file not found at {file_path}")
    
    try:
        with open(file_path, 'r', errors='ignore') as file:
            content = file.read()
            
        # Parse hydrograph data into a flat list for easier DataFrame creation
        ts_data = []  # List to hold dicts: {'grid_id': id, 'time': time, 'discharge': flow}
        
        # Split content into sections by element header
        sections = re.split(r"^\s+ELEMENT\s+TIME \(HRS\)\s+DISCHARGE \(CFS\)", content, flags=re.MULTILINE)
        
        section_count = 0
        if len(sections) > 1:
            for section in sections[1:]:  # Skip the text before the first header
                lines = section.strip().split('\n')
                if not lines:
                    continue
                
                current_element_id = None
                try:
                    # Process first line which contains the first data point and element ID
                    first_match = re.match(r"^\s*(\d+)\s+([\d.]+)\s+([\d.]+)", lines[0])
                    if not first_match:
                        logger.warning(f"Could not parse first line of section {section_count + 1}: '{lines[0]}'")
                        continue
                    
                    current_element_id = int(first_match.group(1))
                    time_value = float(first_match.group(2))
                    discharge_value = float(first_match.group(3))
                    ts_data.append({
                        GRID_ID: current_element_id,
                        TIME: time_value,
                        DISCHARGE: discharge_value
                    })
                    
                    # Process remaining lines for this element
                    for line in lines[1:]:
                        # Only time and discharge expected in subsequent lines
                        match = re.match(r"^\s+([\d.]+)\s+([\d.]+)", line)
                        if match:
                            time_value = float(match.group(1))
                            discharge_value = float(match.group(2))
                            ts_data.append({
                                GRID_ID: current_element_id,
                                TIME: time_value,
                                DISCHARGE: discharge_value
                            })
                    
                    section_count += 1
                    
                except (ValueError, IndexError) as e:
                    id_str = f" for element {current_element_id}" if current_element_id is not None else ""
                    logger.warning(f"Error parsing data in section {section_count + 1}{id_str}: {e}. Skipping section.")
                    continue
        
        if not ts_data:
            logger.warning("No time series data found in OUTNQ.OUT")
            return pd.DataFrame()
        
        # Create DataFrame from the list of dicts
        raw_ts_df = pd.DataFrame(ts_data)
        
        # Pivot the table: time as index, grid_id as columns, discharge as values
        try:
            time_series_df = raw_ts_df.pivot_table(
                index=TIME,
                columns=GRID_ID,
                values=DISCHARGE,
                aggfunc='first'  # In case of duplicates, take first value
            )
            
            # Sort by time index
            time_series_df.sort_index(inplace=True)
            
            # Fill missing values with 0 for consistency
            time_series_df = time_series_df.fillna(0)
            
            # Set index name for clarity
            time_series_df.index.name = 'Time (hours)'
            
            logger.info(f"Successfully extracted time series data from {section_count} outflow elements with {len(time_series_df)} time steps")
            return time_series_df
            
        except Exception as e:
            logger.error(f"Failed to pivot time series data: {e}", exc_info=True)
            return pd.DataFrame()
            
    except IOError as e:
        logger.error(f"Error reading OUTNQ.OUT file: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error processing OUTNQ.OUT file: {e}", exc_info=True)
        return pd.DataFrame()


def extract_outnq_data(folder_path):
    """
    Extract both summary and time series data from OUTNQ.OUT file.
    
    Args:
        folder_path (str): Path to the directory containing OUTNQ.OUT file.
        
    Returns:
        tuple: (summary_df, time_series_df) where:
            - summary_df: DataFrame with max discharge and time to peak
            - time_series_df: DataFrame with time series data
                     
    Raises:
        FileNotFoundError: If OUTNQ.OUT file is not found.
    """
    summary_df = extract_outnq_summary(folder_path)
    time_series_df = extract_outnq_time_series(folder_path)
    
    return summary_df, time_series_df 
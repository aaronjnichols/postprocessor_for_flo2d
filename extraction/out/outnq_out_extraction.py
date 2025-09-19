import os
import re
import logging
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, TIME, MAX_Q_OUTNQ, TIME_PEAK, DISCHARGE, normalize_grid_id
from core.logger import setup_logger


def _extract_outnq_summary(folder_path):
    """
    Extract summary statistics from OUTNQ.OUT file.
    
    Args:
        folder_path (str): Path to the directory containing OUTNQ.OUT file.
        
    Returns:
        pd.DataFrame: DataFrame with columns [GRID_ID, MAX_Q, TIME_PEAK] containing
                     maximum discharge and time to peak for each outflow element.
                     
    Raises:
        FileNotFoundError: If OUTNQ.OUT file is not found.
        ValueError: If no valid data found in file.
        RuntimeError: If error reading file.
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
            raise ValueError(f"No maximum discharge data found in {file_path}")
        
        # Build summary dataframe from regex matches
        summary_data = []
        for grid_id_str, max_q_str, time_str in max_q_matches:
            try:
                grid_id = int(grid_id_str)
                max_q = float(max_q_str)
                time_peak = float(time_str)
                summary_data.append({
                    GRID_ID: grid_id,
                    MAX_Q_OUTNQ: max_q,
                    TIME_PEAK: time_peak
                })
            except ValueError as e:
                logger.warning(f"Could not parse max Q data: ID={grid_id_str}, Q={max_q_str}, T={time_str}. Error: {e}")
                continue
        
        if not summary_data:
            raise ValueError(f"No valid maximum discharge data found in {file_path}")
        
        summary_df = pd.DataFrame(summary_data)

        # Ensure proper data types
        summary_df[GRID_ID] = pd.to_numeric(summary_df[GRID_ID], errors='coerce').astype('Int64')
        summary_df[MAX_Q_OUTNQ] = pd.to_numeric(summary_df[MAX_Q_OUTNQ], errors='coerce')
        summary_df[TIME_PEAK] = pd.to_numeric(summary_df[TIME_PEAK], errors='coerce')

        # Normalize grid ids to internal 0-based convention
        if not summary_df.empty and GRID_ID in summary_df.columns:
            summary_df[GRID_ID] = summary_df[GRID_ID].apply(
                lambda v: normalize_grid_id(int(v)) if pd.notna(v) else v
            )
        
        logger.info(f"Successfully extracted {len(summary_df)} outflow summary records from OUTNQ.OUT")
        return summary_df
        
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except IOError as e:
        raise RuntimeError(f"Error reading OUTNQ.OUT file: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error processing OUTNQ.OUT file: {e}") from e


def _extract_outnq_time_series(folder_path):
    """
    Extract time series hydrograph data from OUTNQ.OUT file.
    
    Args:
        folder_path (str): Path to the directory containing OUTNQ.OUT file.
        
    Returns:
        pd.DataFrame: DataFrame with time as index and grid IDs as columns,
                     containing discharge values.
                     
    Raises:
        FileNotFoundError: If OUTNQ.OUT file is not found.
        ValueError: If no valid time series data found.
        RuntimeError: If error reading or processing file.
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
            raise ValueError("No time series data found in OUTNQ.OUT")
        
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

            # Columns are the (1-based) element ids used in OUTNQ; convert to 0-based
            # Ensure columns are numeric first
            try:
                time_series_df.columns = pd.to_numeric(time_series_df.columns, errors='coerce').astype('Int64')
                time_series_df.rename(columns=lambda c: normalize_grid_id(int(c)) if pd.notna(c) else c, inplace=True)
            except Exception:
                # If conversion fails, leave as-is; downstream code will handle/log
                pass
            
            # Sort by time index
            time_series_df.sort_index(inplace=True)
            
            # Fill missing values with 0 for consistency
            time_series_df = time_series_df.fillna(0)
            
            # Set index name for clarity
            time_series_df.index.name = 'Time (hours)'
            
            logger.info(f"Successfully extracted time series data from {section_count} outflow elements with {len(time_series_df)} time steps")
            return time_series_df
            
        except Exception as e:
            raise RuntimeError(f"Failed to pivot time series data: {e}") from e
            
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except IOError as e:
        raise RuntimeError(f"Error reading OUTNQ.OUT file: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error processing OUTNQ.OUT file: {e}") from e


@time_function
def extract_outnq_out(folder_path):
    """
    Extract outflow data from OUTNQ.OUT file.
    
    This function extracts both summary statistics and time series hydrograph data
    for outflow elements from FLO-2D model output.
    
    Args:
        folder_path (str): Path to the directory containing OUTNQ.OUT file
        
    Returns:
        dict: Dictionary containing:
            - 'summary': DataFrame with max discharge and time to peak for each element
            - 'time_series': DataFrame with time series hydrograph data
                     
    Raises:
        FileNotFoundError: If OUTNQ.OUT file is not found
        ValueError: If no valid data found in file
        RuntimeError: If error reading or processing file
    """
    file_path = os.path.join(folder_path, 'OUTNQ.OUT')
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"OUTNQ.OUT file not found at {file_path}")
    
    # Extract both summary and time series data
    summary_df = _extract_outnq_summary(folder_path)
    time_series_df = _extract_outnq_time_series(folder_path)
    
    return {
        'summary': summary_df,
        'time_series': time_series_df
    }


def extract_outnq_summary(folder_path) -> pd.DataFrame:
    """Convenience wrapper that returns only the normalized OUTNQ summary table.

    This is used by the model orchestrator for grid-mergeable attributes.
    """
    return _extract_outnq_summary(folder_path)
 

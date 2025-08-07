import os
import logging
import pandas as pd
from core.logger import setup_logger
from core.constants import normalize_grid_id


def extract_inflow_dat(folder_path):
    """
    Extract inflow hydrograph data from INFLOW.DAT file.
    
    Args:
        folder_path (str): Path to the directory containing INFLOW.DAT file.
        
    Returns:
        pd.DataFrame: DataFrame with time as index and grid IDs as columns,
                     containing flow values. Returns empty DataFrame on error.
                     
    Raises:
        FileNotFoundError: If INFLOW.DAT file is not found.
    """
    logger = setup_logger('INFLOW', level=logging.INFO)
    file_path = os.path.join(folder_path, 'INFLOW.DAT')
    
    if not os.path.exists(file_path):
        logger.error(f"INFLOW.DAT file not found at {file_path}")
        raise FileNotFoundError(f"INFLOW.DAT file not found at {file_path}")
    
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            
        # Store data as {grid_id: {time: flow}} to handle different time steps per grid
        hydrograph_data = {}
        current_cell = None
        all_time_steps = set()
        
        for line_num, line in enumerate(lines, 1):
            parts = line.split()
            if not parts:
                continue
                
            if parts[0] == 'F':
                # Extract grid element ID from the last part and validate
                try:
                    raw_grid_id = int(parts[-1])
                    # Normalize grid ID to match coordinate data (1-based to 0-based)
                    current_cell = normalize_grid_id(raw_grid_id)
                    if current_cell not in hydrograph_data:
                        hydrograph_data[current_cell] = {}
                except (ValueError, IndexError) as e:
                    logger.warning(f"Invalid grid ID in line {line_num}: {line.strip()}. Error: {e}")
                    current_cell = None
                    continue
                    
            elif parts[0] == 'H' and current_cell is not None:
                try:
                    time_step = float(parts[1])
                    flow_value = float(parts[2])
                    
                    # Store flow value for this time step
                    hydrograph_data[current_cell][time_step] = flow_value
                    
                    # Track all unique time steps
                    all_time_steps.add(time_step)
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Invalid hydrograph data in line: {line.strip()}. Error: {e}")
                    continue
                    
        if not hydrograph_data:
            logger.warning(f"No inflow data found in {file_path}")
            return pd.DataFrame()
        
        # Create sorted list of all time steps
        sorted_time_steps = sorted(all_time_steps)
        
        # Create a dictionary to hold series data for each grid element
        series_dict = {}
        
        # Create series for each grid element, filling missing time steps with NaN
        for grid_element, time_flow_dict in hydrograph_data.items():
            series_data = pd.Series(time_flow_dict, index=sorted_time_steps)
            series_dict[grid_element] = series_data
        
        # Create DataFrame from the series dictionary
        df = pd.concat(series_dict, axis=1)
        
        # Fill missing data with 0 as default to maintain consistency
        df = df.fillna(0)
        df.index.name = 'Time (hours)'
        
        # Ensure column names are integers for proper merging
        df.columns = df.columns.astype(int)
        
        logger.info(f"Successfully extracted inflow data for {len(df.columns)} grid elements with {len(df)} time steps")
        logger.info(f"Grid ID range: {df.columns.min()} to {df.columns.max()}")
        return df
        
    except IOError as e:
        logger.error(f"Error reading INFLOW.DAT file: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error processing INFLOW.DAT file: {e}", exc_info=True)
        return pd.DataFrame()
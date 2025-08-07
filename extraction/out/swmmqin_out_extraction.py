import os
import re
import pandas as pd
from core.utilities import time_function
from core.constants import TIME, DISCHARGE


def _extract_swmmqin_hydrograph_data(folder_path):
    """
    Extract hydrograph data from the SWMMQIN.OUT file.
    
    Args:
        folder_path (str): Path to the folder containing SWMMQIN.OUT file.
    
    Returns:
        dict: Dictionary of inlet data with inlet names as keys and DataFrames as values.
        
    Raises:
        FileNotFoundError: If SWMMQIN.OUT file is not found.
        ValueError: If no valid data found in file.
        RuntimeError: If error reading file.
    """
    file_path = os.path.join(folder_path, 'SWMMQIN.OUT')
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"SWMMQIN.OUT file not found at {file_path}")
    
    try:
        with open(file_path, 'r') as file:
            file_content = file.readlines()
        
        inlets_data = {}
        current_inlet = None
        pattern_inlet = re.compile(r'STORM DRAIN INLET: +(.*)')
        pattern_data = re.compile(r'^\s*([\d\.]+)\s+([\d\.]+)')
        
        for line in file_content:
            inlet_match = pattern_inlet.search(line)
            data_match = pattern_data.search(line)

            if inlet_match:
                current_inlet = inlet_match.group(1).strip()
                inlets_data[current_inlet] = {TIME: [], DISCHARGE: []}
            
            elif data_match and current_inlet:
                try:
                    time = float(data_match.group(1))
                    discharge = float(data_match.group(2))
                    inlets_data[current_inlet][TIME].append(time)
                    inlets_data[current_inlet][DISCHARGE].append(discharge)
                except ValueError:
                    continue  # Skip invalid data lines
        
        if not inlets_data:
            raise ValueError(f"No valid SWMM inlet data found in {file_path}")
        
        # Convert to DataFrame
        inlet_dfs = {inlet: pd.DataFrame(data) for inlet, data in inlets_data.items()}
        return inlet_dfs
        
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error reading SWMMQIN.OUT file: {e}") from e


@time_function
def extract_swmmqin_out(folder_path):
    """
    Extract SWMM inlet hydrograph data from SWMMQIN.OUT file.
    
    This function extracts storm drain inlet hydrograph time series data
    from FLO-2D SWMM model output.
    
    Args:
        folder_path (str): Path to the directory containing SWMMQIN.OUT file
    
    Returns:
        dict: Dictionary of inlet data with inlet names as keys and DataFrames as values.
              Each DataFrame contains TIME and DISCHARGE columns.
              
    Raises:
        FileNotFoundError: If SWMMQIN.OUT file is not found.
        ValueError: If no valid data found in file.
        RuntimeError: If error reading file.
    """
    file_path = os.path.join(folder_path, 'SWMMQIN.OUT')
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"SWMMQIN.OUT file not found at {file_path}")
    
    # Extract hydrograph data
    return _extract_swmmqin_hydrograph_data(folder_path)
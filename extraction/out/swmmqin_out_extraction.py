import os
import re
import pandas as pd
from core.constants import TIME, DISCHARGE


def extract_hydrograph_data(folder_path):
    """
    Extracts hydrograph data from the SWMMQIN.OUT file.
    
    Args:
        folder_path (str): Path to the folder containing SWMMQIN.OUT file.
    
    Returns:
        dict: Dictionary of inlet data with inlet names as keys and DataFrames as values.
    """
    file_path = os.path.join(folder_path, 'SWMMQIN.OUT')
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"SWMMQIN.OUT file not found at {file_path}")
    
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
            time = float(data_match.group(1))
            discharge = float(data_match.group(2))
            inlets_data[current_inlet][TIME].append(time)
            inlets_data[current_inlet][DISCHARGE].append(discharge)
    
    # Convert to DataFrame
    inlet_dfs = {inlet: pd.DataFrame(data) for inlet, data in inlets_data.items()}
    return inlet_dfs


def extract_swmmqin_out(file_path):
    """
    Wrapper function for extract_hydrograph_data to maintain consistency with other extraction modules.
    
    Args:
        file_path (str): Path to the project directory containing SWMMQIN.OUT file.
    
    Returns:
        dict: Dictionary of inlet data with inlet names as keys and DataFrames as values.
    """
    return extract_hydrograph_data(file_path)
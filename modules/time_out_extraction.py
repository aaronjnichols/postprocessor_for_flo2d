import pandas as pd
from .constants import GRID_ID, NUM_TIME_DECREMENTS, normalize_grid_id

def extract_time_out_data(file_path):
    """
    Extracts data from the TIME.OUT file.
    Handles both FLOODPLAIN NODES and CHANNEL NODES sections.

    Args:
        file_path (str): Path to the TIME.OUT file.

    Returns:
        pandas.DataFrame: DataFrame containing the extracted data.
    """
    grid_ids = []
    num_time_decrements = []

    with open(file_path, 'r') as file:
        lines = file.readlines()
        
    extract_data = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # Start extracting when we hit either floodplain or channel nodes section
        if (line_stripped.startswith("FLOODPLAIN NODES    NUMBER OF TIMES EXCEEDED") or 
            line_stripped.startswith("CHANNEL NODES")):
            extract_data = True
            continue

        # Stop extracting when we hit the timestep decreases section
        if line_stripped.startswith("THE LAST"):
            extract_data = False
            continue
            
        # Skip empty lines
        if not line_stripped:
            continue
        
        # Extract data if we're in a data section
        if extract_data:
            parts = line_stripped.split()
            if len(parts) == 2:
                try:
                    # Try to convert both parts to numbers
                    grid_id = normalize_grid_id(int(parts[0]))
                    time_decrements = int(parts[1])
                    grid_ids.append(grid_id)
                    num_time_decrements.append(time_decrements)
                except ValueError:
                    # Skip lines with non-numeric data (headers, etc.)
                    continue

    return pd.DataFrame({GRID_ID: grid_ids, NUM_TIME_DECREMENTS: num_time_decrements})

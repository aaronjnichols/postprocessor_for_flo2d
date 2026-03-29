import os
import re
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, NUM_TIME_DECREMENTS, normalize_grid_id
from core.path_resolver import resolve_model_file_path


@time_function
def extract_time_out(folder_path):
    """
    Extract time decrement data from TIME.OUT file.
    
    This function extracts the number of time decrements for each grid element
    from both FLOODPLAIN NODES and CHANNEL NODES sections.

    Args:
        folder_path (str): Path to the directory containing TIME.OUT file

    Returns:
        pd.DataFrame: DataFrame with columns [GRID_ID, NUM_TIME_DECREMENTS]
        
    Raises:
        FileNotFoundError: If TIME.OUT file is not found
        ValueError: If no valid data found in file
        RuntimeError: If error reading file
    """
    file_path = resolve_model_file_path(folder_path, 'TIME.OUT')
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"TIME.OUT file not found at {file_path}")
    
    try:
        with open(file_path, 'r') as file:
            text = file.read()

        sections = re.split(r'FLOODPLAIN NODES\s+NUMBER OF TIMES EXCEEDED|CHANNEL NODES', text)[1:]
        data = []
        
        for section in sections:
            for line in section.splitlines():
                if line.startswith('THE LAST'):
                    break
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    try:
                        grid_id = int(parts[0])
                        time_decrements = int(parts[1])
                        data.append((grid_id, time_decrements))
                    except ValueError:
                        continue  # Skip invalid data lines

        if not data:
            raise ValueError(f"No valid time decrement data found in {file_path}")

        df = pd.DataFrame(data, columns=[GRID_ID, NUM_TIME_DECREMENTS])
        if not df.empty:
            df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
        
        return df
        
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error reading TIME.OUT file: {e}") from e

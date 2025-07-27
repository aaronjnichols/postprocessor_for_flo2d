import re
import pandas as pd
from core.constants import GRID_ID, NUM_TIME_DECREMENTS, normalize_grid_id

def extract_time_out_data(file_path):
    """
    Extracts data from the TIME.OUT file.
    Handles both FLOODPLAIN NODES and CHANNEL NODES sections.

    Args:
        file_path (str): Path to the TIME.OUT file.

    Returns:
        pandas.DataFrame: DataFrame containing the extracted data.
    """
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
                data.append((int(parts[0]), int(parts[1])))

    df = pd.DataFrame(data, columns=[GRID_ID, NUM_TIME_DECREMENTS])
    if not df.empty:
        df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

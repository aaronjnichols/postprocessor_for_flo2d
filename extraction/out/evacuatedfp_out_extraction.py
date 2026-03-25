import pandas as pd
from core.constants import GRID_ID, NUM_EVACUATIONS, normalize_grid_id
from core.path_resolver import resolve_model_file_path

def extract_evacuatedfp_out(file_path):
    """
    Extracts data from the EVACUATEDFP.OUT file.

    Args:
        file_path (str): Path to the EVACUATEDFP.OUT file.

    Returns:
        pandas.DataFrame: DataFrame containing the extracted data.
    """
    file_path = resolve_model_file_path(file_path, 'EVACUATEDFP.OUT')

    grid_ids = []
    num_evacuations = []

    with open(file_path, 'r') as file:
        lines = file.readlines()
        
    extract_data = False
    for line in lines:
        if line.strip().startswith("ELEMENT    NUMBER OF EVACUATIONS"):
            extract_data = True
            continue
        
        if extract_data and line.strip():
            parts = line.split()
            if len(parts) == 2:
                try:
                    grid_ids.append(int(parts[0]))
                    num_evacuations.append(int(parts[1]))
                except ValueError:
                    # Skip lines with non-numeric data
                    continue

    df = pd.DataFrame({GRID_ID: grid_ids, NUM_EVACUATIONS: num_evacuations})
    if not df.empty and GRID_ID in df.columns:
        df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

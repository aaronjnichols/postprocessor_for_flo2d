import os
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, normalize_grid_id

@time_function
def extract_veloc_out(path, relevant_grid_ids=None):
    """Extract velocity results from VELOC.OUT"""
    file_path = os.path.join(path, 'VELOC.OUT')
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.split()
            grid_id = normalize_grid_id(int(parts[0]))  # Convert to 0-based
            if relevant_grid_ids is None or grid_id in relevant_grid_ids:
                data.append((grid_id, float(parts[3])))
    return pd.DataFrame(data, columns=[GRID_ID, 'velocity'])

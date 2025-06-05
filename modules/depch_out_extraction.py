import os
import pandas as pd
from .utilities import time_function

@time_function
def extract_depch_out(path, relevant_grid_ids=None):
    """Extract channel depth results from DEPCH.OUT"""
    file_path = os.path.join(path, 'DEPCH.OUT')
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.split()
            grid_id = int(parts[0])
            if relevant_grid_ids is None or grid_id in relevant_grid_ids:
                data.append((grid_id, float(parts[3])))
    return pd.DataFrame(data, columns=['FLO-2D Grid ID', 'DEPCH'])

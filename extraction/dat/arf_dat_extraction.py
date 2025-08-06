import sys
import pandas as pd
import numpy as np
from core.utilities import time_function
from core.constants import normalize_grid_id, GRID_ID, AREA_REDUCTION_FACTOR

@time_function
def extract_arf_dat(file_path):
    '''
    Extracts grid IDs and Area Reduction Factors from a file.

    Parameters:
        file_path (str): The path to the file to be processed.

    Returns:
        pd.DataFrame: A DataFrame containing 'grid_id' and 'arf' columns.
    '''
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.split()
            if parts:
                if parts[0] == 'T':
                    grid_id = normalize_grid_id(int(parts[1]))
                    arf = 1.0
                else:
                    try:
                        grid_id = normalize_grid_id(int(parts[0]))
                        arf = float(parts[1])
                    except ValueError:
                        continue
                data.append((grid_id, arf))

    df = pd.DataFrame(data, columns=[GRID_ID, AREA_REDUCTION_FACTOR])
    return df


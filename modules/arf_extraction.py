import sys
import pandas as pd
import numpy as np
from modules.utilities import time_function
from .constants import normalize_grid_id, GRID_ID, AREA_REDUCTION_FACTOR

@time_function
def extract_area_reduction_factors(file_path):
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

@time_function
def merge_arf_with_model_data(model_data, arf_df):
    '''
    Merges ARF data with the model data.

    Parameters:
        model_data (pd.DataFrame): The main model data.
        arf_df (pd.DataFrame): The ARF data.

    Returns:
        pd.DataFrame: The merged DataFrame.
    '''
    merged_df = pd.merge(model_data, arf_df, on=GRID_ID, how='left')
    merged_df[AREA_REDUCTION_FACTOR] = merged_df[AREA_REDUCTION_FACTOR].fillna(1.0)
    return merged_df
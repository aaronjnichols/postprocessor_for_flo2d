import os
import pandas as pd
from .extraction_utils import read_with_dask_optimized
from .constants import GRID_ID, X_COORD, Y_COORD, DEPTH_MAX, normalize_grid_id


def extract_depth_out(path):
    file_path = os.path.join(path, 'DEPTH.OUT')
    df = read_with_dask_optimized(file_path, column_names=[GRID_ID, X_COORD, Y_COORD, DEPTH_MAX]).compute()
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

import os
import pandas as pd
from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, X_COORD, Y_COORD, DEPTH_MAX, normalize_grid_id


def extract_depth_out(path):
    file_path = os.path.join(path, 'DEPTH.OUT')
    df = read_with_dask_optimized(file_path, column_names=[GRID_ID, X_COORD, Y_COORD, DEPTH_MAX]).compute()
    # Vectorized normalize_grid_id: 1-based to 0-based
    df[GRID_ID] = df[GRID_ID].astype('int64') - 1
    return df

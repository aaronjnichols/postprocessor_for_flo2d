import os
import pandas as pd
from .extraction_utils import read_with_dask_optimized


def extract_depth_out(path):
    file_path = os.path.join(path, 'DEPTH.OUT')
    df = read_with_dask_optimized(file_path, column_names=['grid_id', 'x', 'y', 'depth_max']).compute()
    df['grid_id'] = df['grid_id'] - 1
    return df

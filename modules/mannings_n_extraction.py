import os
from .extraction_utils import read_with_dask_optimized


def extract_mannings_n(path):
    file_path = os.path.join(path, 'MANNINGS_N.DAT')
    df = read_with_dask_optimized(file_path, column_names=['grid_id', 'mannings_n']).compute()
    df['grid_id'] = df['grid_id'] - 1
    return df

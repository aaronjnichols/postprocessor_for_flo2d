import os
from .extraction_utils import read_with_dask_optimized


def extract_timeoneft_out(path):
    file_path = os.path.join(path, 'TIMEONEFT.OUT')
    df = read_with_dask_optimized(file_path, column_names=['grid_id', 'x', 'y', 'time_of_oneft']).compute()
    df['grid_id'] = df['grid_id'] - 1
    return df

import os
from .extraction_utils import read_with_dask_optimized
from .constants import GRID_ID, X_COORD, Y_COORD, TIME_TO_PEAK, normalize_grid_id


def extract_timetopeak_out(path):
    file_path = os.path.join(path, 'TIMETOPEAK.OUT')
    df = read_with_dask_optimized(file_path, column_names=[GRID_ID, X_COORD, Y_COORD, TIME_TO_PEAK]).compute()
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

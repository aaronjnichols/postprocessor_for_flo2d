import os
from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, X_COORD, Y_COORD, TIME_TWOFT, normalize_grid_id

def extract_timetwoft_out(path):
    file_path = os.path.join(path, 'TIMETWOFT.OUT')
    df = read_with_dask_optimized(file_path, column_names=[GRID_ID, X_COORD, Y_COORD, TIME_TWOFT]).compute()
    df[GRID_ID] = df[GRID_ID].astype('int64') - 1
    return df

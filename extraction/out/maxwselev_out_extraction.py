import os
from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, X_COORD, Y_COORD, MAX_WS_ELEVATION, normalize_grid_id

def extract_maxwselev_out(path):
    file_path = os.path.join(path, 'MAXWSELEV.OUT')
    df = read_with_dask_optimized(file_path, column_names=[GRID_ID, X_COORD, Y_COORD, MAX_WS_ELEVATION]).compute()
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

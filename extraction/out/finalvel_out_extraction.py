import os
from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, X_COORD, Y_COORD, FINAL_VELOCITY, normalize_grid_id


def extract_finalvel_out(path):
    file_path = os.path.join(path, 'FINALVEL.OUT')
    df = read_with_dask_optimized(file_path, column_names=[GRID_ID, X_COORD, Y_COORD, FINAL_VELOCITY]).compute()
    df[GRID_ID] = df[GRID_ID].astype('int64') - 1
    return df

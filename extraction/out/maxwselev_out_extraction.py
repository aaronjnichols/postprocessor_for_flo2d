import os
from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, X_COORD, Y_COORD, WSE_MAX, normalize_grid_id
from core.path_resolver import resolve_model_file_path

def extract_maxwselev_out(path):
    file_path = resolve_model_file_path(path, 'MAXWSELEV.OUT')
    df = read_with_dask_optimized(file_path, column_names=[GRID_ID, X_COORD, Y_COORD, WSE_MAX]).compute()
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

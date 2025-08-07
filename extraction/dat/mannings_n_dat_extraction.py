import os
from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, MANNINGS_N, normalize_grid_id


def extract_mannings_n_dat(path):
    file_path = os.path.join(path, 'MANNINGS_N.DAT')
    df = read_with_dask_optimized(file_path, column_names=[GRID_ID, MANNINGS_N]).compute()
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

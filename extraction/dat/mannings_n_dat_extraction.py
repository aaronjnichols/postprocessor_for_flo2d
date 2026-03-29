from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, MANNINGS_N, X_COORD, Y_COORD, normalize_grid_id
from core.path_resolver import resolve_model_file_path


def extract_mannings_n_dat(path):
    file_path = resolve_model_file_path(path, 'MANNINGS_N.DAT')
    df = read_with_dask_optimized(
        file_path,
        column_names=[GRID_ID, X_COORD, Y_COORD, MANNINGS_N],
    ).compute()
    df = df[[GRID_ID, MANNINGS_N]].copy()
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

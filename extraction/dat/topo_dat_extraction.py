import os
from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, X_COORD, Y_COORD, TOPO_ELEVATION
from core.path_resolver import resolve_model_file_path


def extract_topo_dat(path):
    """
    Extract topographic data from TOPO.DAT file.
    
    TOPO.DAT format: X_COORD Y_COORD TOPO_ELEVATION
    Grid IDs correspond to line numbers (0-based indexing).
    
    Args:
        path (str): Path to the directory containing TOPO.DAT file.
        
    Returns:
        pd.DataFrame: DataFrame with grid_id, x, y, and elev columns.
    """
    file_path = resolve_model_file_path(path, 'TOPO.DAT')
    df = read_with_dask_optimized(file_path, column_names=[X_COORD, Y_COORD, TOPO_ELEVATION]).compute()
    
    # Generate sequential grid IDs starting from 0 (corresponding to line numbers)
    df.insert(0, GRID_ID, range(len(df)))
    
    return df

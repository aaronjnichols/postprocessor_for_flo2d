import os
import pandas as pd
from extraction.base.extraction_utils import read_with_dask_optimized
from core.constants import GRID_ID, Q_MAX, FLOW_DIRECTION, normalize_grid_id
from core.path_resolver import resolve_model_file_path

def extract_maxqhyd_out(path):
    file_path = resolve_model_file_path(path, 'MAXQHYD.OUT')
    df = read_with_dask_optimized(file_path, column_names=None, skiprows=4).compute()
    df = df[df.iloc[:, 0] >= 1]
    if df.empty:
        return pd.DataFrame(columns=[GRID_ID, Q_MAX, FLOW_DIRECTION])
    # Column 7 contains max discharge (cfs), 8 contains flow direction
    df = df.iloc[:, [0, 7, 8]].rename(columns={0: GRID_ID, 7: Q_MAX, 8: FLOW_DIRECTION})
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

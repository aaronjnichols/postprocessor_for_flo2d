import os
import pandas as pd
from .extraction_utils import read_with_dask_optimized
from .constants import GRID_ID, VELOCITY_MAX, FLOW_DIRECTION, normalize_grid_id


def extract_maxqhyd_out(path):
    file_path = os.path.join(path, 'MAXQHYD.OUT')
    df = read_with_dask_optimized(file_path, column_names=None, skiprows=4).compute()
    df = df[df.iloc[:, 0] >= 1]
    if df.empty:
        return pd.DataFrame(columns=[GRID_ID, VELOCITY_MAX, FLOW_DIRECTION])
    df = df.iloc[:, [0, 7, 8]].rename(columns={0: GRID_ID, 7: VELOCITY_MAX, 8: FLOW_DIRECTION})
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

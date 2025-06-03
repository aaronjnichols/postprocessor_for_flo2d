import os
import pandas as pd
from .extraction_utils import read_with_dask_optimized


def extract_maxqhyd_out(path):
    file_path = os.path.join(path, 'MAXQHYD.OUT')
    df = read_with_dask_optimized(file_path, column_names=None, skiprows=4).compute()
    df = df[df.iloc[:, 0] >= 1]
    if df.empty:
        return pd.DataFrame(columns=['grid_id', 'q_max', 'flow_direction'])
    df = df.iloc[:, [0, 7, 8]].rename(columns={0: 'grid_id', 7: 'q_max', 8: 'flow_direction'})
    df['grid_id'] = df['grid_id'] - 1
    return df

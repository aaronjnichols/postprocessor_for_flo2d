import os
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, normalize_grid_id
from extraction.base.extraction_utils import read_with_dask_optimized
from core.path_resolver import resolve_model_file_path


@time_function
def extract_depch_out(path, relevant_grid_ids=None):
    """Extract channel depth results from DEPCH.OUT using vectorized parsing."""
    file_path = resolve_model_file_path(path, 'DEPCH.OUT')

    # Dask-optimized read for scalability on large files
    ddf = read_with_dask_optimized(
        file_path,
        column_names=[GRID_ID, 'x', 'y', 'channel_depth'],
        usecols=[0, 3],
        dtype={GRID_ID: 'int64', 'channel_depth': 'float64'},
    )
    df = ddf.compute()

    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)

    if relevant_grid_ids is not None:
        df = df[df[GRID_ID].isin(relevant_grid_ids)]

    df['channel_depth'] = pd.to_numeric(df['channel_depth'], downcast='float')
    return df.reset_index(drop=True)

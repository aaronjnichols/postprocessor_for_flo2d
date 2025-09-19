import os
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, VELOCITY_CHANNEL, normalize_grid_id
from extraction.base.extraction_utils import read_with_dask_optimized


@time_function
def extract_veloc_out(path, relevant_grid_ids=None):
    """Extract velocity results from VELOC.OUT using vectorized parsing.

    This reader uses pandas.read_csv with explicit column selection and dtypes
    for improved performance on large files.
    """
    file_path = os.path.join(path, 'VELOC.OUT')

    # Dask-optimized read for scalability on large files
    ddf = read_with_dask_optimized(
        file_path,
        column_names=[GRID_ID, 'x', 'y', VELOCITY_CHANNEL],
        usecols=[0, 3],
        dtype={GRID_ID: 'int64', VELOCITY_CHANNEL: 'float64'},
    )
    df = ddf.compute()

    # Normalize GRID_ID to 0-based
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)

    if relevant_grid_ids is not None:
        df = df[df[GRID_ID].isin(relevant_grid_ids)]

    # Downcast velocity to float32 to reduce memory footprint
    df[VELOCITY_CHANNEL] = pd.to_numeric(df[VELOCITY_CHANNEL], downcast='float')
    return df.reset_index(drop=True)

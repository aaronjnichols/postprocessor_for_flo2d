import os
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, normalize_grid_id


@time_function
def extract_veloc_out(path, relevant_grid_ids=None):
    """Extract velocity results from VELOC.OUT using vectorized parsing.

    This reader uses pandas.read_csv with explicit column selection and dtypes
    for improved performance on large files.
    """
    file_path = os.path.join(path, 'VELOC.OUT')

    # Read only the first (grid id) and fourth (velocity) whitespace-separated fields
    df = pd.read_csv(
        file_path,
        delim_whitespace=True,
        header=None,
        usecols=[0, 3],
        names=[GRID_ID, 'velocity'],
        dtype={0: 'int64', 3: 'float64'},
        engine='python',
    )

    # Normalize GRID_ID to 0-based
    df[GRID_ID] = df[GRID_ID].astype('int64') - 1

    if relevant_grid_ids is not None:
        df = df[df[GRID_ID].isin(relevant_grid_ids)]

    # Downcast velocity to float32 to reduce memory footprint
    df['velocity'] = pd.to_numeric(df['velocity'], downcast='float')
    return df.reset_index(drop=True)

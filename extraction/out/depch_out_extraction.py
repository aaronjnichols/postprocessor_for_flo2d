import os
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, normalize_grid_id


@time_function
def extract_depch_out(path, relevant_grid_ids=None):
    """Extract channel depth results from DEPCH.OUT using vectorized parsing."""
    file_path = os.path.join(path, 'DEPCH.OUT')

    df = pd.read_csv(
        file_path,
        delim_whitespace=True,
        header=None,
        usecols=[0, 3],
        names=[GRID_ID, 'channel_depth'],
        dtype={0: 'int64', 3: 'float64'},
        engine='python',
    )

    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)

    if relevant_grid_ids is not None:
        df = df[df[GRID_ID].isin(relevant_grid_ids)]

    df['channel_depth'] = pd.to_numeric(df['channel_depth'], downcast='float')
    return df.reset_index(drop=True)

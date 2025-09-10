import os
import pandas as pd
from core.utilities import time_function
from core.constants import (
    GRID_ID,
    NODE,
    MAX_DISCHARGE,
    TIME_MAX_DISCHARGE,
    MAX_STAGE,
    TIME_MAX_STAGE,
    normalize_grid_id,
)

@time_function
def extract_chanmax_out(path):
    """Extract channel maximum results from CHANMAX.OUT"""
    file_path = os.path.join(path, 'CHANMAX.OUT')
    data = []
    with open(file_path, 'r', encoding='ISO-8859-1') as file:
        for line in file:
            if line.strip() and not line.startswith('CHANNEL SEGMENT NO'):
                try:
                    node, max_discharge, time_max_discharge, max_stage, time_max_stage = line.split()
                    data.append((int(node), float(max_discharge), float(time_max_discharge),
                                 float(max_stage), float(time_max_stage)))
                except ValueError:
                    continue
    df = pd.DataFrame(
        data,
        columns=[
            NODE,
            MAX_DISCHARGE,
            TIME_MAX_DISCHARGE,
            MAX_STAGE,
            TIME_MAX_STAGE
        ]
    )
    # Rename and normalize channel node id to standard internal id (0-based)
    if NODE in df.columns:
        df = df.rename(columns={NODE: GRID_ID})
    if GRID_ID in df.columns and not df.empty:
        df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    return df

import os
import pandas as pd
from .utilities import time_function
from .constants import NODE, normalize_grid_id, MAX_DISCHARGE, TIME_MAX_DISCHARGE, MAX_STAGE, TIME_MAX_STAGE

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
                    data.append((normalize_grid_id(int(node)), float(max_discharge), float(time_max_discharge),
                                 float(max_stage), float(time_max_stage)))
                except ValueError:
                    continue
    return pd.DataFrame(
        data,
        columns=[
            NODE,
            MAX_DISCHARGE,
            TIME_MAX_DISCHARGE,
            MAX_STAGE,
            TIME_MAX_STAGE
        ]
    )

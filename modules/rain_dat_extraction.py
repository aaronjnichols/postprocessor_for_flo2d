import os
import pandas as pd
from .constants import GRID_ID, RAIN_DEPTH


def extract_rain_data(path):
    rain_file = os.path.join(path, 'RAIN.DAT')
    with open(rain_file, 'r') as file:
        lines = file.readlines()

    multiplier_value = float(lines[1].split()[0])
    last_r_index = max(i for i, line in enumerate(lines) if line.startswith('R'))
    data_lines = lines[last_r_index + 1:]

    data = [line.split() for line in data_lines if line.strip()]
    df = pd.DataFrame(data, columns=[GRID_ID, RAIN_DEPTH])

    df[GRID_ID] = pd.to_numeric(df[GRID_ID], errors='coerce').astype('Int64')
    df[RAIN_DEPTH] = pd.to_numeric(df[RAIN_DEPTH], errors='coerce') * multiplier_value

    return df

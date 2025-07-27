import os
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, normalize_grid_id

@time_function
def extract_chan_dat(path):
    """Extract channel alignment data from CHAN.DAT"""
    file_path = os.path.join(path, 'CHAN.DAT')
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip() and line[0].isalpha():
                parts = line.split()
                data.append((parts[0], normalize_grid_id(int(parts[1])), float(parts[2]), float(parts[3]), int(parts[4])))
    return pd.DataFrame(
        data,
        columns=[
            'cross_section_type',
            GRID_ID,
            'manning_n',
            'length_to_next_xsec',
            'cross_section_number'
        ]
    )

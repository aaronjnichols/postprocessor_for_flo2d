import os
import pandas as pd
from .utilities import time_function

@time_function
def extract_chan_dat(path):
    """Extract channel alignment data from CHAN.DAT"""
    file_path = os.path.join(path, 'CHAN.DAT')
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip() and line[0].isalpha():
                parts = line.split()
                data.append((parts[0], int(parts[1]), float(parts[2]), float(parts[3]), int(parts[4])))
    return pd.DataFrame(
        data,
        columns=[
            'Cross Section Type',
            'FLO-2D Grid ID',
            'N-Value',
            'Length to Next Cross Section',
            'Cross Section Number'
        ]
    )

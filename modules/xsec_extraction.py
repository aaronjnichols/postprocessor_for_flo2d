import os
import pandas as pd
from .utilities import time_function
from .constants import CROSS_SECTION_NUMBER, STATION, ELEVATION

@time_function
def extract_xsec_dat(path):
    """Extract cross section geometry from XSEC.DAT"""
    file_path = os.path.join(path, 'XSEC.DAT')
    data = []
    with open(file_path, 'r') as file:
        cross_section = None
        for line in file:
            if line.startswith('X'):
                cross_section = int(line.split()[1])
            elif line.strip():
                station, elevation = map(float, line.split())
                data.append((cross_section, station, elevation))
    return pd.DataFrame(data, columns=[CROSS_SECTION_NUMBER, STATION, ELEVATION])

import os
import pandas as pd
from core.utilities import time_function
from core.constants import CROSS_SECTION_NUMBER, STATION, ELEVATION
from core.path_resolver import resolve_model_file_path

@time_function
def extract_xsec_dat(path):
    """Extract cross section geometry from XSEC.DAT"""
    file_path = resolve_model_file_path(path, 'XSEC.DAT')
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

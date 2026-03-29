import os
import pandas as pd
from core.constants import GRID_ID, FPXSEC, normalize_grid_id
from core.path_resolver import resolve_model_file_path


def extract_fpxsec_dat(path):
    fpxsec_file = resolve_model_file_path(path, 'FPXSEC.DAT')
    if not os.path.exists(fpxsec_file):
        return pd.DataFrame()

    rows = []
    with open(fpxsec_file, 'r') as file:
        line_number = 0
        for line in file:
            parts = line.split()
            if parts and parts[0] == 'X':
                line_number += 1
                for grid_id in parts[3:]:
                    if grid_id.isdigit():
                        rows.append({GRID_ID: normalize_grid_id(int(grid_id)), FPXSEC: line_number})
    return pd.DataFrame(rows)

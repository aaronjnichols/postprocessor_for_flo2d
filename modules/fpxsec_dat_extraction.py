import os
import pandas as pd


def extract_fpxsec_dat(path):
    fpxsec_file = os.path.join(path, 'FPXSEC.DAT')
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
                        rows.append({'grid_id': int(grid_id) - 1, 'fpxsec': line_number})
    return pd.DataFrame(rows)

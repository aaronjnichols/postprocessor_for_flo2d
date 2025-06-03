import os
import pandas as pd


def extract_infil_dat(path):
    infil_file = os.path.join(path, 'INFIL.DAT')
    with open(infil_file, 'r') as file:
        for _ in range(3):
            next(file)
        data = []
        for line in file:
            parts = line.strip().split()
            if parts and parts[0] == 'F':
                data.append(parts[1:])

    columns = ['grid_id', 'xksat', 'psif', 'dtheta', 'abstrinf', 'rtimpf', 'soil_depth']
    df = pd.DataFrame(data, columns=columns)
    return df.apply(pd.to_numeric, errors='coerce')

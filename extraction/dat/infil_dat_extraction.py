import os
import pandas as pd
from core.constants import GRID_ID, XKSAT, PSIF, DTHETA, ABSTRINF, RTIMPF, SOIL_DEPTH


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

    columns = [GRID_ID, XKSAT, PSIF, DTHETA, ABSTRINF, RTIMPF, SOIL_DEPTH]
    df = pd.DataFrame(data, columns=columns)
    return df.apply(pd.to_numeric, errors='coerce')

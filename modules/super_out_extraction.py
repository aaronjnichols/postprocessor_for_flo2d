import os
import pandas as pd


def extract_super_out(path):
    super_file = os.path.join(path, 'SUPER.OUT')
    with open(super_file, 'r') as file:
        lines = file.readlines()

    data_lines = lines[7:]
    data = []
    for line in data_lines:
        parts = line.split()
        if len(parts) == 5:
            data.append({
                'grid_id': int(parts[0]) - 1,
                'max_froude_no': float(parts[1]),
                'depth_super': float(parts[2]),
                'time_super': float(parts[3]),
                'num_supercritical_timesteps': int(parts[4])
            })
    return pd.DataFrame(data)

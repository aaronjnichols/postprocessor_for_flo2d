import os
import pandas as pd
from .utilities import time_function

@time_function
def extract_chanmax_out(path):
    """Extract channel maximum results from CHANMAX.OUT"""
    file_path = os.path.join(path, 'CHANMAX.OUT')
    data = []
    with open(file_path, 'r', encoding='ISO-8859-1') as file:
        for line in file:
            if line.strip() and not line.startswith('CHANNEL SEGMENT NO'):
                try:
                    node, max_discharge, time_max_discharge, max_stage, time_max_stage = line.split()
                    data.append((int(node), float(max_discharge), float(time_max_discharge),
                                 float(max_stage), float(time_max_stage)))
                except ValueError:
                    continue
    return pd.DataFrame(
        data,
        columns=[
            'NODE',
            'Max Discharge (CFS)',
            'Time of Max Discharge (Hrs)',
            'Max Stage',
            'Time of Max Stage (Hrs)'
        ]
    )

import os

import pandas as pd

from core.utilities import time_function
from core.constants import normalize_grid_id, GRID_ID, AREA_REDUCTION_FACTOR
from core.path_resolver import resolve_model_file_path


def _resolve_arf_dat_path(path: str) -> str:
    """Accept either a project directory or an explicit ARF.DAT file path."""
    return resolve_model_file_path(path, "ARF.DAT")


def _resolve_arf_dat_path(path: str) -> str:
    """Accept either a project directory or an explicit ARF.DAT file path."""
    if os.path.isdir(path):
        return os.path.join(path, 'ARF.DAT')
    return path

@time_function
def extract_arf_dat(path: str) -> pd.DataFrame:
    """
    Extract grid IDs and Area Reduction Factors from ARF.DAT.

    Parameters:
        path (str): Path to ARF.DAT or the project directory containing it.

    Returns:
        pd.DataFrame: DataFrame containing normalized grid IDs and ARF values.
    """
    file_path = _resolve_arf_dat_path(path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ARF.DAT file not found at {file_path}")

    data = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.split()
            if parts:
                if parts[0] == 'T':
                    grid_id = normalize_grid_id(int(parts[1]))
                    arf = 1.0
                else:
                    try:
                        grid_id = normalize_grid_id(int(parts[0]))
                        arf = float(parts[1])
                    except ValueError:
                        continue
                data.append((grid_id, arf))

    df = pd.DataFrame(data, columns=[GRID_ID, AREA_REDUCTION_FACTOR])
    return df


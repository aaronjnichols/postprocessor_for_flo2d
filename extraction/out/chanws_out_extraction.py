"""Extract per-element maximum water surface from CHANWS.OUT."""

from __future__ import annotations

import os

import pandas as pd

from core.utilities import time_function
from core.path_resolver import resolve_model_file_path

_INVALID_SENTINEL = -999.0


@time_function
def extract_chanws_out(folder_path: str) -> pd.DataFrame:
    """Parse CHANWS.OUT and return a per-element max WSE table.

    Returns:
        pd.DataFrame: Columns ['element_id', 'x', 'y', 'max_wse'].
    """
    file_path = resolve_model_file_path(folder_path, "CHANWS.OUT")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CHANWS.OUT file not found at {file_path}")

    rows = []
    with open(file_path, "r", encoding="ISO-8859-1", errors="ignore") as file:
        for line in file:
            parts = line.split()
            if len(parts) != 4:
                continue
            if not parts[0].isdigit():
                continue
            try:
                element_id = int(parts[0])
                x_coord = float(parts[1])
                y_coord = float(parts[2])
                max_wse = float(parts[3])
            except ValueError:
                continue

            if max_wse <= _INVALID_SENTINEL:
                max_wse = float("nan")
            rows.append((element_id, x_coord, y_coord, max_wse))

    return pd.DataFrame(rows, columns=["element_id", "x", "y", "max_wse"])

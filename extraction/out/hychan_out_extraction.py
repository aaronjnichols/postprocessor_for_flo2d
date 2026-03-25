"""Extract channel element hydrographs from HYCHAN.OUT."""

from __future__ import annotations

import os
import re
from typing import Dict, List

import pandas as pd

from core.utilities import time_function
from core.path_resolver import resolve_model_file_path

_BLOCK_START_RE = re.compile(r"CHANNEL HYDROGRAPH FOR ELEMENT NO:\s*(\d+)")

_COLUMNS = [
    "time",
    "elev",
    "depth",
    "velocity",
    "discharge",
    "froude_no",
    "flow_area",
    "wetted_perimeter",
    "hydraulic_radius",
    "top_width",
    "width_depth",
    "energy_slope",
    "bed_shear_stress",
    "surface_area",
]


def _to_numeric_row(line: str):
    parts = line.split()
    if len(parts) < len(_COLUMNS):
        return None
    try:
        return [float(value) for value in parts[: len(_COLUMNS)]]
    except ValueError:
        return None


@time_function
def extract_hychan_out(folder_path: str) -> Dict[int, pd.DataFrame]:
    """Parse HYCHAN.OUT and return per-element hydrograph tables.

    Returns:
        Dict[int, pd.DataFrame]: Mapping element_id -> hydrograph DataFrame.
    """
    file_path = resolve_model_file_path(folder_path, "HYCHAN.OUT")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"HYCHAN.OUT file not found at {file_path}")

    hydrographs: Dict[int, List[List[float]]] = {}
    current_element = None

    with open(file_path, "r", encoding="ISO-8859-1", errors="ignore") as file:
        for raw_line in file:
            match = _BLOCK_START_RE.search(raw_line)
            if match:
                current_element = int(match.group(1))
                hydrographs.setdefault(current_element, [])
                continue

            if current_element is None:
                continue

            row = _to_numeric_row(raw_line)
            if row is None:
                continue
            hydrographs[current_element].append(row)

    result = {}
    for element_id, rows in hydrographs.items():
        if not rows:
            continue
        df = pd.DataFrame(rows, columns=_COLUMNS)
        df = df.sort_values("time").reset_index(drop=True)
        result[element_id] = df

    return result

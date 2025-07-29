"""Utilities for extracting data from FLO-2D LEVEE.DAT files."""

import warnings
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd

from core.constants import (
    RAISELEV,
    ILEVFAIL,
    LGRIDNO,
    LGRIDNO_ORIGINAL,
    REPORT_OVERTOP,
    LINE_NUMBER,
    LDIR,
    LEVCREST,
    DIRECTION_NAME,
    LFAILGRID,
    LFAILGRID_ORIGINAL,
    IS_GLOBAL,
    LFAILDIR,
    FAILEVEL,
    FAILTIME,
    LEVBASE,
    FAILWIDTHMAX,
    FAILRATE,
    FAILWIDRATE,
    GFRAGCHAR,
    GFRAGPROB,
    LEVFRAGRID,
    LEVFRAGCHAR,
    LEVFRAGPROB,
)


def _get_direction_name(direction: int) -> str:
    """Return compass direction name for a direction number."""
    direction_map = {
        1: "North",
        2: "East",
        3: "South",
        4: "West",
        5: "Northeast",
        6: "Southeast",
        7: "Southwest",
        8: "Northwest",
    }
    return direction_map.get(direction, f"Unknown({direction})")


def _create_summary(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create simple summary statistics for parsed levee data."""
    summary_rows = []
    for key, df in data.items():
        if key == "header":
            continue
        summary_rows.append(
            {"data_type": key, "record_count": len(df), "has_data": not df.empty}
        )
    return pd.DataFrame(summary_rows)


def extract_levee_dat(file_path: Union[str, Path]) -> Dict[str, pd.DataFrame]:
    """Parse LEVEE.DAT into structured DataFrames."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"LEVEE.DAT file not found: {file_path}")

    result: Dict[str, pd.DataFrame] = {}
    containers = {
        "levee_elements": [],
        "levee_directions": [],
        "failure_elements": [],
        "failure_parameters": [],
        "global_fragility": [],
        "individual_fragility": [],
    }

    with file_path.open("r") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise ValueError("File is empty")

    header_parts = lines[0].split()
    if len(header_parts) < 2:
        raise ValueError("Invalid header format")

    result["header"] = pd.DataFrame(
        [{RAISELEV: float(header_parts[0]), ILEVFAIL: int(header_parts[1])}]
    )

    current_levee_element = None
    for idx, line in enumerate(lines[1:], start=2):
        parts = line.split()
        if not parts:
            continue
        line_type = parts[0].upper()

        try:
            if line_type == "L":
                grid_no = int(parts[1])
                current_levee_element = grid_no
                containers["levee_elements"].append(
                    {
                        LGRIDNO: abs(grid_no),
                        LGRIDNO_ORIGINAL: grid_no,
                        REPORT_OVERTOP: grid_no < 0,
                        LINE_NUMBER: idx,
                    }
                )

            elif line_type == "D":
                if current_levee_element is None:
                    warnings.warn(
                        f"D line found without preceding L line at line {idx}"
                    )
                    continue
                direction = int(parts[1])
                crest = float(parts[2])
                if direction not in range(1, 9):
                    warnings.warn(
                        f"Invalid direction {direction} at line {idx}"
                    )
                containers["levee_directions"].append(
                    {
                        LGRIDNO: abs(current_levee_element),
                        LDIR: direction,
                        LEVCREST: crest,
                        DIRECTION_NAME: _get_direction_name(direction),
                        LINE_NUMBER: idx,
                    }
                )

            elif line_type == "F":
                fail_grid = int(parts[1])
                containers["failure_elements"].append(
                    {
                        LFAILGRID: abs(fail_grid),
                        LFAILGRID_ORIGINAL: fail_grid,
                        IS_GLOBAL: fail_grid < 0,
                        LINE_NUMBER: idx,
                    }
                )

            elif line_type == "W":
                containers["failure_parameters"].append(
                    {
                        LFAILDIR: int(parts[1]),
                        FAILEVEL: float(parts[2]),
                        FAILTIME: float(parts[3]),
                        LEVBASE: float(parts[4]),
                        FAILWIDTHMAX: float(parts[5]),
                        FAILRATE: float(parts[6]),
                        FAILWIDRATE: float(parts[7]),
                        DIRECTION_NAME: _get_direction_name(int(parts[1])),
                        LINE_NUMBER: idx,
                    }
                )

            elif line_type == "C":
                containers["global_fragility"].append(
                    {
                        GFRAGCHAR: parts[1],
                        GFRAGPROB: float(parts[2]),
                        LINE_NUMBER: idx,
                    }
                )

            elif line_type == "P":
                containers["individual_fragility"].append(
                    {
                        LEVFRAGRID: int(parts[1]),
                        LEVFRAGCHAR: parts[2],
                        LEVFRAGPROB: float(parts[3]),
                        LINE_NUMBER: idx,
                    }
                )

            else:
                warnings.warn(f"Unknown line type '{line_type}' at line {idx}")

        except (ValueError, IndexError) as exc:
            warnings.warn(f"Error parsing line {idx}: {exc}")

    for key, container in containers.items():
        result[key] = pd.DataFrame(container)

    result["summary"] = _create_summary(result)
    return result


def validate_levee_data(data: Dict[str, pd.DataFrame]) -> List[str]:
    """Validate parsed levee data for basic consistency."""
    warnings_list: List[str] = []

    ilevfail = 0
    if not data.get("header", pd.DataFrame()).empty:
        ilevfail = data["header"][ILEVFAIL].iloc[0]

    has_failure = (
        len(data.get("failure_elements", [])) > 0
        or len(data.get("failure_parameters", [])) > 0
    )

    if ilevfail == 0 and has_failure:
        warnings_list.append("ILEVFAIL=0 but failure data found")
    elif ilevfail > 0 and not has_failure:
        warnings_list.append("ILEVFAIL>0 but no failure data found")

    if not data.get("levee_elements", pd.DataFrame()).empty and not data.get(
        "levee_directions", pd.DataFrame()
    ).empty:
        levee_ids = set(data["levee_elements"][LGRIDNO])
        direction_ids = set(data["levee_directions"][LGRIDNO])
        orphaned = direction_ids - levee_ids
        if orphaned:
            warnings_list.append(
                f"Directions found for non-existent levee elements: {sorted(orphaned)}"
            )

    if not data.get("levee_directions", pd.DataFrame()).empty:
        invalid_dirs = data["levee_directions"][
            ~data["levee_directions"][LDIR].isin(range(1, 9))
        ]
        if not invalid_dirs.empty:
            warnings_list.append(
                f"Invalid directions found: {invalid_dirs[LDIR].tolist()}"
            )

    if not data.get("levee_elements", pd.DataFrame()).empty:
        duplicates = data["levee_elements"][LGRIDNO].duplicated()
        if duplicates.any():
            dup_ids = data["levee_elements"][duplicates][LGRIDNO].tolist()
            warnings_list.append(f"Duplicate levee elements found: {dup_ids}")

    return warnings_list

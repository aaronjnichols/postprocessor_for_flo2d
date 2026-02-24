"""Common helpers for parsing SWMM ``*.rpt`` files.

Provides function-based helpers for extracting node and link summaries and
time-series from SWMM report files. Shared by the junction, outfall, and
link extractors to keep behavior consistent and implementation concise.
"""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from core.constants import EXT_FLOW


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Section markers and regex patterns used throughout the module
# ---------------------------------------------------------------------------

SECTION_MARKERS = {
    "node_summary": "Node Summary",
    "continuity_errors": "Highest Continuity Errors",
    "depth_summary": "Node Depth Summary",
    "inflow_summary": "Node Inflow Summary",
    "surcharge_summary": "Node Surcharge Summary",
    "flooding_summary": "Node Flooding Summary",
    "outfall_loading": "Outfall Loading Summary",
}

EXTRACTION_MAP = None  # Will be defined after extractor functions are declared

NODE_HEADER_PATTERN = re.compile(r"<<< Node (.*?) >>>")
NODE_DATA_PATTERN = re.compile(
    r"(\w{3}-\d{2}-\d{4})\s+(\d{2}:\d{2}:\d{2})\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"
)
NODE_CONT_ERROR_PATTERN = re.compile(
    r"Node\s+([A-Za-z0-9_\-]+)\s+\(?(-?[\d\.]+)\s*%?\)?\s*$"
)


# ---------------------------------------------------------------------------
# Link-specific section markers and regex patterns (for link extraction)
# ---------------------------------------------------------------------------

LINK_SECTION_MARKERS = {
    "link_flow": "Link Flow Summary",
    "conduit_surcharge": "Conduit Surcharge Summary",
    "flow_classification": "Flow Classification Summary",
}

LINK_HEADER_PATTERN = re.compile(r"<<< Link (.*?) >>>")
LINK_DATA_PATTERN = re.compile(
    r"(\w{3}-\d{2}-\d{4})\s+(\d{2}:\d{2}:\d{2})\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"
)

# ---------------------------------------------------------------------------
# File reading and generic parsing helpers
# ---------------------------------------------------------------------------

def _find_rpt_file(directory: str) -> str:
    """Return the first file ending with ``.rpt`` in ``directory``.

    Args:
        directory: Path to the model directory.

    Returns:
        Path to the report file.

    Raises:
        FileNotFoundError: If no report file is found.
    """

    for filename in os.listdir(directory):
        if filename.lower().endswith(".rpt"):
            return os.path.join(directory, filename)
    raise FileNotFoundError(f"No .rpt file found in {directory}")


def _read_file_content(file_path: str) -> List[str]:
    """Read file content handling basic encoding issues.

    Tries UTF-8 first, falls back to latin-1.
    """

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except UnicodeDecodeError:
        logger.warning("UTF-8 decoding failed, trying latin-1.")
        with open(file_path, "r", encoding="latin-1") as f:
            return f.readlines()


def _parse_sections_generic(
    raw_lines: Iterable[str], markers: Dict[str, str], header_skip: int = 2
) -> Dict[str, List[str]]:
    """Parse summary sections from ``raw_lines`` using provided markers.

    Args:
        raw_lines: Iterable of report file lines.
        markers: Mapping of section key -> header text to match.
        header_skip: Number of lines to skip after a section header.

    Returns:
        Dict mapping section keys to their content lines.
    """

    sections: Dict[str, List[str]] = {key: [] for key in markers}
    current_key: Optional[str] = None
    skip_lines = 0
    for line in raw_lines:
        stripped = line.strip()
        marker_found = False
        for key, marker in markers.items():
            if stripped.lstrip("* ").startswith(marker):
                current_key = key
                skip_lines = header_skip
                marker_found = True
                break
        if marker_found:
            continue
        if skip_lines > 0:
            skip_lines -= 1
            continue
        if current_key and not stripped:
            current_key = None
            continue
        if current_key and not stripped.startswith(("---", "***")):
            sections[current_key].append(stripped)
    return sections


def _parse_sections(raw_lines: Iterable[str]) -> Dict[str, List[str]]:
    """Parse known node summary sections from ``raw_lines``."""
    return _parse_sections_generic(raw_lines, SECTION_MARKERS, header_skip=2)


# ---------------------------------------------------------------------------
# Generic helpers used by extraction routines
# ---------------------------------------------------------------------------

def _parse_time_parts(parts: List[str], start_index: int) -> str:
    """Parse a SWMM summary time field, preserving days when present.

    Looks for the first token containing a ``:`` (for example, ``14:02``)
    at or after ``start_index``. If the immediately preceding token is an
    integer, treat it as ``days`` and include it (e.g., ``0 14:02``).
    """
    idx_time: Optional[int] = None
    for i in range(start_index, len(parts)):
        if ":" in parts[i]:
            idx_time = i
            break
    if idx_time is None:
        return ""
    time_token = parts[idx_time]
    if idx_time - 1 >= start_index:
        days_token = parts[idx_time - 1]
        if days_token.isdigit():
            return f"{days_token} {time_token}"
    return time_token


def _parse_end_numeric(parts: List[str], num_expected: int) -> List[Optional[float]]:
    """Parse the last ``num_expected`` numeric tokens from ``parts``.

    Returns a list of floats or ``None`` when parsing fails or values are
    missing.
    """
    numeric_parts = [p for p in parts if re.match(r"^-?\d+(\.\d+)?(E[+-]\d+)?$", p)]
    if len(numeric_parts) >= num_expected:
        try:
            return [float(p) for p in numeric_parts[-num_expected:]]
        except ValueError:
            return [None] * num_expected
    return [None] * num_expected


def _index_to_hours_since_start(df: pd.DataFrame, time_col_name: str = "Time") -> pd.DataFrame:
    """Convert datetime index to hours since first timestamp and expose as column.

    - Attempts to parse the existing index as ``%b-%d-%Y %H:%M:%S``.
    - Drops rows where all columns are NaN after parsing.
    - Resets index to a column named ``time``.
    """
    if df.empty:
        return df
    try:
        df.index = pd.to_datetime(df.index, format="%b-%d-%Y %H:%M:%S", errors="coerce")
        df.dropna(axis=0, how="all", inplace=True)
    except Exception:  # pragma: no cover - fallback if parsing fails
        pass
    df.index.name = time_col_name
    df.reset_index(inplace=True)
    if time_col_name in df.columns:
        start_time = df[time_col_name].min()
        try:
            df[time_col_name] = (df[time_col_name] - start_time).dt.total_seconds() / 3600.0
        except Exception:
            # If datetime arithmetic fails, leave the column as-is
            pass
        df.rename(columns={time_col_name: "time"}, inplace=True)
    return df


def _extract_entity_time_series_multi(
    raw_lines: Iterable[str],
    header_pattern: re.Pattern,
    data_pattern: re.Pattern,
    metric_names: List[str],
) -> Dict[str, pd.DataFrame]:
    """Generic multi-metric time-series extractor for entities (nodes/links).

    Returns one wide DataFrame per metric with:
    - ``time`` column (hours since start)
    - one column per entity id
    """
    metric_data: Dict[str, Dict[str, Dict[str, float]]] = {
        metric: defaultdict(dict) for metric in metric_names
    }
    current_entity: Optional[str] = None

    for line in raw_lines:
        head_match = header_pattern.search(line)
        if head_match:
            current_entity = head_match.group(1).strip()
            continue
        if not current_entity:
            continue

        data_match = data_pattern.search(line)
        if data_match:
            date, time_str, *groups = data_match.groups()
            datetime_str = f"{date} {time_str}"
            for metric_idx, metric_name in enumerate(metric_names):
                if metric_idx >= len(groups):
                    break
                try:
                    metric_value = float(groups[metric_idx])
                except (TypeError, ValueError):
                    continue
                metric_data[metric_name][current_entity][datetime_str] = metric_value
        elif not line.strip() or line.strip().startswith("<<<"):
            current_entity = None

    results: Dict[str, pd.DataFrame] = {}
    for metric_name in metric_names:
        data = metric_data.get(metric_name, {})
        if not data:
            results[metric_name] = pd.DataFrame()
            continue
        df = pd.DataFrame.from_dict(data, orient="columns")
        results[metric_name] = _index_to_hours_since_start(df)
    return results


# ---------------------------------------------------------------------------
# Extraction functions for specific sections
# ---------------------------------------------------------------------------

def _extract_node_time_series_multi(raw_lines) -> Dict[str, pd.DataFrame]:
    """Extract node time-series for all supported SWMM node metrics."""
    return _extract_entity_time_series_multi(
        raw_lines,
        NODE_HEADER_PATTERN,
        NODE_DATA_PATTERN,
        metric_names=["total_inflow", "flooding", "depth", "head"],
    )


def _extract_node_time_series(raw_lines):
    """Extract total inflow time series data for all nodes (legacy key)."""
    return _extract_node_time_series_multi(raw_lines).get("total_inflow", pd.DataFrame())


def _extract_node_summary(content: Iterable[str]) -> pd.DataFrame:
    data: List[dict] = []
    for line in content:
        parts = line.split()
        if len(parts) >= 5:
            try:
                row = {
                    "node_id": parts[0],
                    "type": parts[1],
                    "inv_elev": float(parts[2]),
                    "max_depth": float(parts[3]),
                    "pond_area": float(parts[4]),
                }
                # External inflow may be present as an additional numeric column
                if len(parts) >= 6:
                    try:
                        row[EXT_FLOW] = float(parts[5])
                    except ValueError:
                        # Keep it absent if not numeric
                        pass
                data.append(row)
            except ValueError:
                continue
    return pd.DataFrame(data)


def _extract_highest_continuity_error(raw_lines: Iterable[str]) -> Dict[str, float]:
    errors: Dict[str, float] = {}
    for line in raw_lines:
        if line.strip().startswith("Node"):
            match = NODE_CONT_ERROR_PATTERN.search(line.strip())
            if match:
                try:
                    errors[match.group(1)] = float(match.group(2))
                except ValueError:
                    pass
    return errors


def _extract_node_depth_summary(content: Iterable[str]) -> Dict[str, dict]:
    data: Dict[str, dict] = {}
    for line in content:
        parts = line.split()
        if len(parts) >= 6:
            try:
                time_str = _parse_time_parts(parts, 5)
                data[parts[0]] = {
                    "Avg_Depth": float(parts[2]),
                    "Max_Depth": float(parts[3]),
                    "Max_HGL": float(parts[4]),
                    "Time_of_Max_Depth": time_str,
                }
            except (ValueError, IndexError):
                continue
    return data


def _extract_node_inflow_summary(content: Iterable[str]) -> Dict[str, dict]:
    data: Dict[str, dict] = {}
    for line in content:
        parts = line.split()
        if len(parts) >= 8:
            try:
                time_str = _parse_time_parts(parts, 4)
                volumes = _parse_end_numeric(parts, 2)
                data[parts[0]] = {
                    "Max_Lateral_Inflow": float(parts[2]),
                    "Max_Total_Inflow": float(parts[3]),
                    "Time_of_Max_Inflow": time_str,
                    "Lateral_Inflow_Volume": volumes[0],
                    "Total_Inflow_Volume": volumes[1],
                }
            except (ValueError, IndexError):
                continue
    return data


def _extract_node_surcharge_summary(content: Iterable[str]) -> Dict[str, dict]:
    data: Dict[str, dict] = {}
    for line in content:
        parts = line.split()
        if len(parts) >= 5:
            try:
                data[parts[0]] = {
                    "Hours_Surcharged": float(parts[2]),
                    "Max_Height_Above_Crown": float(parts[3]),
                    "Min_Depth_Below_Rim": float(parts[4]),
                }
            except (ValueError, IndexError):
                continue
    return data


def _extract_node_flooding_summary(content: Iterable[str]) -> Dict[str, dict]:
    data: Dict[str, dict] = {}
    for line in content:
        parts = line.split()
        if len(parts) >= 6:
            try:
                time_str = _parse_time_parts(parts, 3)
                vol_depth = _parse_end_numeric(parts, 2)
                data[parts[0]] = {
                    "Hours_Flooded": float(parts[1]),
                    "Max_Flooding_Rate": float(parts[2]),
                    "Time_of_Max_Flooding": time_str,
                    "Total_Flood_Volume": vol_depth[0],
                    "Max_Ponded_Depth": vol_depth[1],
                }
            except (ValueError, IndexError):
                continue
    return data


def _extract_outfall_loading_summary(content: Iterable[str]) -> Dict[str, dict]:
    data: Dict[str, dict] = {}
    for line in content:
        parts = line.split()
        if len(parts) == 5:
            try:
                data[parts[0]] = {
                    "Flow_Freq_Pcnt": float(parts[1]),
                    "Avg_Flow_CFS": float(parts[2]),
                    "Max_Flow_CFS": float(parts[3]),
                    "Total_Volume_MG": float(parts[4]),
                }
            except ValueError:
                continue
    return data


# ---------------------------------------------------------------------------
# Extraction registry (nodes): map section keys to extractor callables
# ---------------------------------------------------------------------------

# key in parsed sections -> (extractor function, results dict key)
EXTRACTION_MAP: Dict[str, Tuple[Callable[[Iterable[str]], dict], str]] = {
    "depth_summary": (_extract_node_depth_summary, "depth_summary"),
    "inflow_summary": (_extract_node_inflow_summary, "inflow_summary"),
    "surcharge_summary": (_extract_node_surcharge_summary, "surcharge_summary"),
    "flooding_summary": (_extract_node_flooding_summary, "flooding_summary"),
    "outfall_loading": (_extract_outfall_loading_summary, "outfall_loading"),
}


def _create_merged_summary_results(
    node_summary,
    continuity_errors,
    depth_summary,
    inflow_summary,
    surcharge_summary,
    flooding_summary,
    outfall_loading,
):
    """Merge individual summary sections into a single DataFrame."""

    base_df = node_summary
    if base_df.empty:
        dicts = [
            depth_summary,
            inflow_summary,
            surcharge_summary,
            flooding_summary,
            continuity_errors,
            outfall_loading,
        ]
        all_nodes = {k for d in dicts for k in d.keys()}
        if all_nodes:
            base_df = pd.DataFrame(list(all_nodes), columns=["node_id"])
        else:
            return pd.DataFrame(columns=["node_id"])

    merged = base_df.copy()

    if continuity_errors:
        cont_df = pd.DataFrame(
            list(continuity_errors.items()),
            columns=["node_id", "Continuity_Error_Pcnt"],
        )
        merged = pd.merge(merged, cont_df, on="node_id", how="left")

    for data_dict in [
        depth_summary,
        inflow_summary,
        surcharge_summary,
        flooding_summary,
        outfall_loading,
    ]:
        if not data_dict:
            continue
        df_to_merge = pd.DataFrame.from_dict(data_dict, orient="index")
        df_to_merge.index.name = "node_id"
        df_to_merge.reset_index(inplace=True)
        merged = pd.merge(merged, df_to_merge, on="node_id", how="left")

    return merged


# ---------------------------------------------------------------------------
# Public extraction function
# ---------------------------------------------------------------------------

def _extract_nodes_rpt(folder_path: str) -> dict:
    """Extract node related data from a SWMM *.rpt file.

    Args:
        folder_path (str): Path to directory containing the report file.

    Returns:
        dict: Dictionary containing:
            - ``node_summary`` (pd.DataFrame)
            - ``continuity_errors`` (dict)
            - ``depth_summary`` (dict)
            - ``inflow_summary`` (dict)
            - ``surcharge_summary`` (dict)
            - ``flooding_summary`` (dict)
            - ``outfall_loading`` (dict)
            - ``node_time_series`` (pd.DataFrame)
            - ``merged_results`` (pd.DataFrame)

    Raises:
        FileNotFoundError: If no report file is found in ``folder_path``.
    """

    file_path = _find_rpt_file(folder_path)
    raw_content = _read_file_content(file_path)

    node_time_series_multi = _extract_node_time_series_multi(raw_content)
    node_time_series_df = node_time_series_multi.get("total_inflow", pd.DataFrame())
    sections = _parse_sections(raw_content)

    node_summary_df = _extract_node_summary(sections.get("node_summary", []))
    continuity_errors = _extract_highest_continuity_error(raw_content)

    # Orchestrate section extraction via registry to avoid duplication
    extracted: Dict[str, dict] = {}
    for section_key, (extractor_fn, result_key) in EXTRACTION_MAP.items():
        extracted[result_key] = extractor_fn(sections.get(section_key, []))

    depth_summary = extracted.get("depth_summary", {})
    inflow_summary = extracted.get("inflow_summary", {})
    surcharge_summary = extracted.get("surcharge_summary", {})
    flooding_summary = extracted.get("flooding_summary", {})
    outfall_loading = extracted.get("outfall_loading", {})

    merged_results = _create_merged_summary_results(
        node_summary_df,
        continuity_errors,
        depth_summary,
        inflow_summary,
        surcharge_summary,
        flooding_summary,
        outfall_loading,
    )

    return {
        "node_summary": node_summary_df,
        "continuity_errors": continuity_errors,
        "depth_summary": depth_summary,
        "inflow_summary": inflow_summary,
        "surcharge_summary": surcharge_summary,
        "flooding_summary": flooding_summary,
        "outfall_loading": outfall_loading,
        "node_time_series": node_time_series_df,
        "node_time_series_multi": node_time_series_multi,
        "merged_results": merged_results,
    }


# ---------------------------------------------------------------------------
# Link extraction helpers and public function
# ---------------------------------------------------------------------------

def _parse_link_sections(raw_lines: Iterable[str]) -> Dict[str, List[str]]:
    """Parse known link summary sections from ``raw_lines``."""
    return _parse_sections_generic(raw_lines, LINK_SECTION_MARKERS, header_skip=2)


def _extract_link_time_series(raw_lines: Iterable[str]) -> pd.DataFrame:
    """Extract flow time series data for all links (legacy key)."""
    return _extract_link_time_series_multi(raw_lines).get("flow", pd.DataFrame())


def _extract_link_time_series_multi(raw_lines: Iterable[str]) -> Dict[str, pd.DataFrame]:
    """Extract link time-series for all supported SWMM link metrics."""
    return _extract_entity_time_series_multi(
        raw_lines,
        LINK_HEADER_PATTERN,
        LINK_DATA_PATTERN,
        metric_names=["flow", "velocity", "depth", "capacity"],
    )


def _extract_link_flow_summary(content: Iterable[str]) -> pd.DataFrame:
    link_flow_data = []
    # Allow censored velocities with leading '>' or '<' in the velocity column (group 6)
    pattern = re.compile(
        r"^\s*(\S+)\s+(\S+)\s+([\d.\-]+)\s+(\d+)\s+([\d:\s]+?)\s+([<>]?[\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"
    )
    def _parse_censored_number(s: str):
        gt = s.startswith('>')
        lt = s.startswith('<')
        try:
            val = float(s.lstrip('><'))
        except ValueError:
            val = None
        return val, gt, lt
    for line in content:
        match = pattern.search(line)
        if match:
            try:
                v, v_gt, v_lt = _parse_censored_number(match.group(6))
                link_flow_data.append(
                    {
                        "link_id": match.group(1),
                        "type": match.group(2),
                        "max_flow": float(match.group(3)),
                        "day_max": int(match.group(4)),
                        "time_max": match.group(5).strip(),
                        "max_vel": float(v) if v is not None else None,
                        "max_vel_gt": v_gt,
                        "max_vel_lt": v_lt,
                        "flow_ratio": float(match.group(7)),
                        "depth_rat": float(match.group(8)),
                    }
                )
            except (ValueError, IndexError):
                continue
    return pd.DataFrame(link_flow_data)


def _extract_conduit_surcharge_summary(content: Iterable[str]) -> pd.DataFrame:
    conduit_surcharge_data = []
    pattern = re.compile(
        r"^\s*(\S+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"
    )
    for line in content:
        match = pattern.search(line)
        if match:
            try:
                conduit_surcharge_data.append(
                    {
                        "link_id": match.group(1),
                        "hrs_full": float(match.group(2)),
                        "hrs_full_u": float(match.group(3)),
                        "hrs_full_d": float(match.group(4)),
                        "hrs_above": float(match.group(5)),
                        "hrs_cap": float(match.group(6)),
                    }
                )
            except (ValueError, IndexError):
                continue
    return pd.DataFrame(conduit_surcharge_data)


def _extract_flow_classification_summary(content: Iterable[str]) -> pd.DataFrame:
    flow_classification_data = []
    pattern = re.compile(
        r"^\s*(\S+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"
    )
    for line in content:
        match = pattern.search(line)
        if match:
            try:
                flow_classification_data.append(
                    {
                        "link_id": match.group(1),
                        "adj_len": float(match.group(2)),
                        "dry_up": float(match.group(3)),
                        "dry_down": float(match.group(4)),
                        "dry_sub": float(match.group(5)),
                        "dry_sup": float(match.group(6)),
                        "crit_up": float(match.group(7)),
                        "crit_down": float(match.group(8)),
                        "froude": float(match.group(9)),
                        "flow_chg": float(match.group(10)),
                    }
                )
            except (ValueError, IndexError):
                continue
    return pd.DataFrame(flow_classification_data)


def _create_links_merged_summary_results(
    link_flow_df: pd.DataFrame,
    conduit_surcharge_df: pd.DataFrame,
    flow_classification_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge individual link summary DataFrames into a single DataFrame."""

    dfs = []
    if not link_flow_df.empty:
        dfs.append(link_flow_df)
    if not conduit_surcharge_df.empty:
        dfs.append(conduit_surcharge_df)
    if not flow_classification_df.empty:
        dfs.append(flow_classification_df)

    if not dfs:
        return pd.DataFrame()

    merged = dfs[0].copy()
    for df_next in dfs[1:]:
        if "link_id" not in merged.columns or "link_id" not in df_next.columns:
            continue
        merged = pd.merge(
            merged, df_next, on="link_id", how="outer", suffixes=(None, "_dup")
        )
        dup_cols = [col for col in merged if col.endswith("_dup")]
        if dup_cols:
            merged.drop(columns=dup_cols, inplace=True)
    return merged


def _extract_links_rpt(folder_path: str) -> dict:
    """Extract link related data from a SWMM ``*.rpt`` file.

    Returns a dict containing:
        - ``link_flow`` (pd.DataFrame)
        - ``conduit_surcharge`` (pd.DataFrame)
        - ``flow_classification`` (pd.DataFrame)
        - ``link_time_series`` (pd.DataFrame)
        - ``merged_results`` (pd.DataFrame)
    """

    file_path = _find_rpt_file(folder_path)
    raw_content = _read_file_content(file_path)

    link_time_series_multi = _extract_link_time_series_multi(raw_content)
    link_time_series_df = link_time_series_multi.get("flow", pd.DataFrame())
    sections = _parse_link_sections(raw_content)

    link_flow_df = _extract_link_flow_summary(sections.get("link_flow", []))
    conduit_surcharge_df = _extract_conduit_surcharge_summary(
        sections.get("conduit_surcharge", [])
    )
    flow_classification_df = _extract_flow_classification_summary(
        sections.get("flow_classification", [])
    )

    merged_results = _create_links_merged_summary_results(
        link_flow_df, conduit_surcharge_df, flow_classification_df
    )

    return {
        "link_flow": link_flow_df,
        "conduit_surcharge": conduit_surcharge_df,
        "flow_classification": flow_classification_df,
        "link_time_series": link_time_series_df,
        "link_time_series_multi": link_time_series_multi,
        "merged_results": merged_results,
    }


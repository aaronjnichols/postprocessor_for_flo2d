"""Extract link information from SWMM *.rpt files.

This module provides a function based extraction interface for SWMM
link report files. It converts the class based implementation from
the original project into a functional style consistent with the
FLO-2D postprocessor codebase.
"""

import logging
import re
from collections import defaultdict

import pandas as pd

from core.utilities import time_function
from .swmm_rpt_base import _find_rpt_file, _read_file_content


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Section markers and regex patterns used throughout the module
# ---------------------------------------------------------------------------

SECTION_MARKERS = {
    "link_flow": "Link Flow Summary",
    "conduit_surcharge": "Conduit Surcharge Summary",
    "flow_classification": "Flow Classification Summary",
}

LINK_HEADER_PATTERN = re.compile(r"<<< Link (.*?) >>>")
LINK_DATA_PATTERN = re.compile(
    r"(\w{3}-\d{2}-\d{4})\s+(\d{2}:\d{2}:\d{2})\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"
)


def _parse_sections(raw_lines):
    """Parse known summary sections from *raw_lines*."""

    sections = {key: [] for key in SECTION_MARKERS}
    current_key = None
    skip_lines = 0
    for line in raw_lines:
        stripped = line.strip()
        marker_found = False
        for key, marker in SECTION_MARKERS.items():
            if stripped.lstrip("* ").startswith(marker):
                current_key = key
                skip_lines = 2
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


# ---------------------------------------------------------------------------
# Extraction functions for specific sections
# ---------------------------------------------------------------------------

def _extract_link_time_series(raw_lines):
    """Extract flow time series data for all links."""

    link_data = defaultdict(dict)
    current_link = None

    for line in raw_lines:
        link_match = LINK_HEADER_PATTERN.search(line)
        if link_match:
            current_link = link_match.group(1).strip()
            continue

        if current_link:
            data_match = LINK_DATA_PATTERN.search(line)
            if data_match:
                date, time, flow_str, _, _, _ = data_match.groups()
                datetime_str = f"{date} {time}"
                try:
                    flow = float(flow_str)
                    link_data[current_link][datetime_str] = flow
                except ValueError:
                    continue
            elif not line.strip() or line.strip().startswith("<<<"):
                current_link = None

    if not link_data:
        return pd.DataFrame()

    df_timeseries = pd.DataFrame.from_dict(link_data, orient="columns")

    try:
        df_timeseries.index = pd.to_datetime(
            df_timeseries.index, format="%b-%d-%Y %H:%M:%S", errors="coerce"
        )
        df_timeseries.dropna(axis=0, how="all", inplace=True)
    except Exception:  # pragma: no cover - fallback if parsing fails
        pass

    df_timeseries.index.name = "Time"
    df_timeseries.reset_index(inplace=True)
    
    # Convert Time to hours since start for plotting
    if not df_timeseries.empty and "Time" in df_timeseries.columns:
        start_time = df_timeseries["Time"].min()
        df_timeseries["Time"] = (df_timeseries["Time"] - start_time).dt.total_seconds() / 3600.0
        
    # Rename Time column to match constant
    if "Time" in df_timeseries.columns:
        df_timeseries.rename(columns={"Time": "time"}, inplace=True)
    return df_timeseries


def _extract_link_flow_summary(content):
    link_flow_data = []
    pattern = re.compile(
        r"^\s*(\S+)\s+(\S+)\s+([\d.\-]+)\s+(\d+)\s+([\d:\s]+?)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"
    )
    for line in content:
        match = pattern.search(line)
        if match:
            try:
                link_flow_data.append(
                    {
                        "link_id": match.group(1),
                        "type": match.group(2),
                        "max_flow": float(match.group(3)),
                        "day_max": int(match.group(4)),
                        "time_max": match.group(5).strip(),
                        "max_vel": float(match.group(6)),
                        "flow_ratio": float(match.group(7)),
                        "depth_rat": float(match.group(8)),
                    }
                )
            except (ValueError, IndexError):
                continue
    return pd.DataFrame(link_flow_data)


def _extract_conduit_surcharge_summary(content):
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


def _extract_flow_classification_summary(content):
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


def _create_merged_summary_results(link_flow_df, conduit_surcharge_df, flow_classification_df):
    """Merge individual summary DataFrames into a single DataFrame."""

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


# ---------------------------------------------------------------------------
# Public extraction function
# ---------------------------------------------------------------------------

@time_function
def extract_swmmlinks_rpt(folder_path):
    """Extract link related data from a SWMM *.rpt file.

    Args:
        folder_path (str): Path to directory containing the report file.

    Returns:
        dict: Dictionary containing:
            - ``link_flow`` (pd.DataFrame)
            - ``conduit_surcharge`` (pd.DataFrame)
            - ``flow_classification`` (pd.DataFrame)
            - ``link_time_series`` (pd.DataFrame)
            - ``merged_results`` (pd.DataFrame)

    Raises:
        FileNotFoundError: If no report file is found in ``folder_path``.
    """

    file_path = _find_rpt_file(folder_path)
    raw_content = _read_file_content(file_path)

    link_time_series_df = _extract_link_time_series(raw_content)
    sections = _parse_sections(raw_content)

    link_flow_df = _extract_link_flow_summary(sections.get("link_flow", []))
    conduit_surcharge_df = _extract_conduit_surcharge_summary(
        sections.get("conduit_surcharge", [])
    )
    flow_classification_df = _extract_flow_classification_summary(
        sections.get("flow_classification", [])
    )

    merged_results = _create_merged_summary_results(
        link_flow_df, conduit_surcharge_df, flow_classification_df
    )

    return {
        "link_flow": link_flow_df,
        "conduit_surcharge": conduit_surcharge_df,
        "flow_classification": flow_classification_df,
        "link_time_series": link_time_series_df,
        "merged_results": merged_results,
    }


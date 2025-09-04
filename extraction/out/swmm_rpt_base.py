"""Common helpers for parsing SWMM ``*.rpt`` files and extracting node data.

The routines here provide a function-based interface for working with
SWMM report files, converting the original class-based implementation into
the functional style used throughout the FLO-2D postprocessor codebase.
Generic utilities such as file discovery and encoding-tolerant reading are
shared by the junction, outfall, and link extractors.
"""

import logging
import os
import re
from collections import defaultdict

import pandas as pd


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

EXTRACTION_MAP = {
    "depth_summary": ("_extract_node_depth_summary", "depth_summary"),
    "inflow_summary": ("_extract_node_inflow_summary", "inflow_summary"),
    "surcharge_summary": ("_extract_node_surcharge_summary", "surcharge_summary"),
    "flooding_summary": ("_extract_node_flooding_summary", "flooding_summary"),
    "outfall_loading": ("_extract_outfall_loading_summary", "outfall_loading"),
}

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
# File reading and basic parsing helpers
# ---------------------------------------------------------------------------

def _find_rpt_file(directory):
    """Return the first file ending with .rpt in *directory*.

    Args:
        directory (str): Path to the model directory.

    Returns:
        str: Path to the report file.

    Raises:
        FileNotFoundError: If no report file is found.
    """

    for filename in os.listdir(directory):
        if filename.lower().endswith(".rpt"):
            return os.path.join(directory, filename)
    raise FileNotFoundError(f"No .rpt file found in {directory}")


def _read_file_content(file_path):
    """Read file content handling basic encoding issues."""

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except UnicodeDecodeError:
        logger.warning("UTF-8 decoding failed, trying latin-1.")
        with open(file_path, "r", encoding="latin-1") as f:
            return f.readlines()


def _parse_sections(raw_lines):
    """Parse known summary sections from *raw_lines*.

    Returns:
        dict: Mapping of section keys to lists of relevant lines.
    """

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
# Generic helpers used by extraction routines
# ---------------------------------------------------------------------------

def _parse_time_parts(parts, start_index):
    """Parse a SWMM summary time field, preserving days when present.

    Looks for the first token containing a ':' (e.g., '14:02') at or after
    start_index. If the immediately preceding token is an integer, it is
    treated as 'days' and included, yielding strings like '0 14:02'.
    Otherwise returns the clock token alone.
    """
    # Find the index of the first token that looks like a clock (contains ':')
    idx_time = None
    for i in range(start_index, len(parts)):
        if ":" in parts[i]:
            idx_time = i
            break
    if idx_time is None:
        return ""
    time_token = parts[idx_time]
    # Check for a days token immediately before the time token
    if idx_time - 1 >= start_index:
        days_token = parts[idx_time - 1]
        if days_token.isdigit():
            return f"{days_token} {time_token}"
    return time_token


def _parse_end_numeric(parts, num_expected):
    numeric_parts = [p for p in parts if re.match(r"^-?\d+(\.\d+)?(E[+-]\d+)?$", p)]
    if len(numeric_parts) >= num_expected:
        try:
            return [float(p) for p in numeric_parts[-num_expected:]]
        except ValueError:
            return [None] * num_expected
    return [None] * num_expected


# ---------------------------------------------------------------------------
# Extraction functions for specific sections
# ---------------------------------------------------------------------------

def _extract_node_time_series(raw_lines):
    """Extract inflow time series data for all nodes."""

    node_data = defaultdict(dict)
    current_node = None

    for line in raw_lines:
        node_match = NODE_HEADER_PATTERN.search(line)
        if node_match:
            current_node = node_match.group(1).strip()
            continue

        if current_node:
            data_match = NODE_DATA_PATTERN.search(line)
            if data_match:
                date, time, inflow_str, _, _, _ = data_match.groups()
                datetime_str = f"{date} {time}"
                try:
                    inflow = float(inflow_str)
                    node_data[current_node][datetime_str] = inflow
                except ValueError:
                    continue
            elif not line.strip() or line.strip().startswith("<<<"):
                current_node = None

    if not node_data:
        return pd.DataFrame()

    df_timeseries = pd.DataFrame.from_dict(node_data, orient="columns")

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


def _extract_node_summary(content):
    data = []
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
                # External Inflow may be present as an additional numeric column
                if len(parts) >= 6:
                    try:
                        row["ext_inflow"] = float(parts[5])
                    except ValueError:
                        # Keep it absent if not numeric
                        pass
                data.append(row)
            except ValueError:
                continue
    return pd.DataFrame(data)


def _extract_highest_continuity_error(raw_lines):
    errors = {}
    for line in raw_lines:
        if line.strip().startswith("Node"):
            match = NODE_CONT_ERROR_PATTERN.search(line.strip())
            if match:
                try:
                    errors[match.group(1)] = float(match.group(2))
                except ValueError:
                    pass
    return errors


def _extract_node_depth_summary(content):
    data = {}
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


def _extract_node_inflow_summary(content):
    data = {}
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


def _extract_node_surcharge_summary(content):
    data = {}
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


def _extract_node_flooding_summary(content):
    data = {}
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


def _extract_outfall_loading_summary(content):
    data = {}
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
        all_nodes = set()
        for d in [
            depth_summary,
            inflow_summary,
            surcharge_summary,
            flooding_summary,
            continuity_errors,
            outfall_loading,
        ]:
            all_nodes.update(d.keys())
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

def _extract_nodes_rpt(folder_path):
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

    node_time_series_df = _extract_node_time_series(raw_content)
    sections = _parse_sections(raw_content)

    node_summary_df = _extract_node_summary(sections.get("node_summary", []))
    continuity_errors = _extract_highest_continuity_error(raw_content)
    depth_summary = _extract_node_depth_summary(sections.get("depth_summary", []))
    inflow_summary = _extract_node_inflow_summary(sections.get("inflow_summary", []))
    surcharge_summary = _extract_node_surcharge_summary(
        sections.get("surcharge_summary", [])
    )
    flooding_summary = _extract_node_flooding_summary(
        sections.get("flooding_summary", [])
    )
    outfall_loading = _extract_outfall_loading_summary(
        sections.get("outfall_loading", [])
    )

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
        "merged_results": merged_results,
    }


# ---------------------------------------------------------------------------
# Link extraction helpers and public function
# ---------------------------------------------------------------------------

def _parse_link_sections(raw_lines):
    """Parse known link summary sections from *raw_lines*.

    Returns:
        dict: Mapping of section keys to lists of relevant lines.
    """

    sections = {key: [] for key in LINK_SECTION_MARKERS}
    current_key = None
    skip_lines = 0
    for line in raw_lines:
        stripped = line.strip()
        marker_found = False
        for key, marker in LINK_SECTION_MARKERS.items():
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


def _extract_link_time_series(raw_lines):
    """Extract flow time series data for all links.

    Returns a DataFrame with a numeric 'time' column (hours since start) and
    one column per link id.
    """

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


def _create_links_merged_summary_results(link_flow_df, conduit_surcharge_df, flow_classification_df):
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


def _extract_links_rpt(folder_path):
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

    link_time_series_df = _extract_link_time_series(raw_content)
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
        "merged_results": merged_results,
    }


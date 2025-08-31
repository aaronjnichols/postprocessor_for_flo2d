"""Extract junction information from SWMM *.rpt files."""

from __future__ import annotations

import pandas as pd

from core.utilities import time_function
from .swmm_rpt_base import _extract_nodes_rpt, _filter_time_series, _filter_dict


@time_function
def extract_swmm_junctions_rpt(folder_path: str) -> dict:
    """Extract junction-related data from a SWMM *.rpt file."""
    data = _extract_nodes_rpt(folder_path)
    merged_results = data.get("merged_results", pd.DataFrame())
    node_time_series = data.get("node_time_series", pd.DataFrame())

    if not merged_results.empty:
        merged_results = merged_results[merged_results["type"] == "JUNCTION"].copy()
        junction_ids = merged_results["node_id"].tolist()
    else:
        junction_ids = []

    node_time_series = _filter_time_series(node_time_series, junction_ids)

    node_summary = data.get("node_summary", pd.DataFrame())
    if not node_summary.empty and junction_ids:
        node_summary = node_summary[node_summary["node_id"].isin(junction_ids)]

    continuity_errors = _filter_dict(data.get("continuity_errors", {}), junction_ids)
    depth_summary = _filter_dict(data.get("depth_summary", {}), junction_ids)
    inflow_summary = _filter_dict(data.get("inflow_summary", {}), junction_ids)
    surcharge_summary = _filter_dict(data.get("surcharge_summary", {}), junction_ids)
    flooding_summary = _filter_dict(data.get("flooding_summary", {}), junction_ids)

    return {
        "node_summary": node_summary,
        "continuity_errors": continuity_errors,
        "depth_summary": depth_summary,
        "inflow_summary": inflow_summary,
        "surcharge_summary": surcharge_summary,
        "flooding_summary": flooding_summary,
        "node_time_series": node_time_series,
        "merged_results": merged_results,
    }

"""Extract junction information from SWMM *.rpt files."""

from __future__ import annotations

import pandas as pd

from core.utilities import time_function
from .swmm_rpt_base import _extract_nodes_rpt


@time_function
def extract_swmm_junctions_rpt(folder_path: str) -> dict:
    """Extract junction-related data from a SWMM *.rpt file."""
    data = _extract_nodes_rpt(folder_path)
    merged_results = data.get("merged_results", pd.DataFrame())
    node_time_series = data.get("node_time_series", pd.DataFrame())
    node_time_series_multi = data.get("node_time_series_multi", {})

    if not merged_results.empty:
        # Be robust to casing differences (e.g., 'Junction', 'JUNCTION')
        type_col = "type"
        if type_col in merged_results.columns:
            mask = merged_results[type_col].astype(str).str.strip().str.upper() == "JUNCTION"
            merged_results = merged_results[mask].copy()
        junction_ids = merged_results["node_id"].tolist() if "node_id" in merged_results.columns else []
    else:
        junction_ids = []

    # Keep raw node time-series unfiltered. Some SWMM reports contain summary
    # formatting that can cause partial ID parsing in summary sections; the
    # time-series headers still carry correct node IDs.

    node_summary = data.get("node_summary", pd.DataFrame())
    if not node_summary.empty and junction_ids:
        node_summary = node_summary[node_summary["node_id"].isin(junction_ids)]

    def filter_dict(d: dict) -> dict:
        return {k: v for k, v in d.items() if k in junction_ids}

    continuity_errors = filter_dict(data.get("continuity_errors", {}))
    depth_summary = filter_dict(data.get("depth_summary", {}))
    inflow_summary = filter_dict(data.get("inflow_summary", {}))
    surcharge_summary = filter_dict(data.get("surcharge_summary", {}))
    flooding_summary = filter_dict(data.get("flooding_summary", {}))

    return {
        "node_summary": node_summary,
        "continuity_errors": continuity_errors,
        "depth_summary": depth_summary,
        "inflow_summary": inflow_summary,
        "surcharge_summary": surcharge_summary,
        "flooding_summary": flooding_summary,
        "node_time_series": node_time_series,
        "node_time_series_multi": node_time_series_multi,
        "merged_results": merged_results,
    }

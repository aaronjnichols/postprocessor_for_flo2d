"""Extract outfall information from SWMM *.rpt files."""

from __future__ import annotations

import pandas as pd

from core.utilities import time_function
from .swmm_rpt_base import (
    _extract_nodes_rpt,
    _filter_time_series,
    _dict_to_filtered_df,
)


@time_function
def extract_swmm_outfalls_rpt(folder_path: str) -> dict:
    """Extract outfall-related data from a SWMM ``*.rpt`` file.

    Returns a dictionary with individual summary sections filtered to outfalls
    along with any available hydrograph time series.
    """

    data = _extract_nodes_rpt(folder_path)

    node_summary = data.get("node_summary", pd.DataFrame())
    node_time_series = data.get("node_time_series", pd.DataFrame())
    depth_summary_dict = data.get("depth_summary", {})
    inflow_summary_dict = data.get("inflow_summary", {})
    outfall_loading_dict = data.get("outfall_loading", {})
    merged_results = data.get("merged_results", pd.DataFrame())

    if not node_summary.empty:
        node_summary = node_summary[node_summary["type"] == "OUTFALL"].copy()
        outfall_ids = node_summary["node_id"].tolist()
    else:
        outfall_ids = []

    depth_df = _dict_to_filtered_df(depth_summary_dict, outfall_ids)
    inflow_df = _dict_to_filtered_df(inflow_summary_dict, outfall_ids)
    loading_df = _dict_to_filtered_df(outfall_loading_dict, outfall_ids)

    node_time_series = _filter_time_series(node_time_series, outfall_ids)

    if not merged_results.empty and outfall_ids:
        merged_results = merged_results[merged_results["node_id"].isin(outfall_ids)].copy()
    else:
        merged_results = pd.DataFrame()

    return {
        "node_summary": node_summary,
        "node_depth_summary": depth_df,
        "node_inflow_summary": inflow_df,
        "outfall_loading_summary": loading_df,
        "outfall_time_series": node_time_series,
        "merged_results": merged_results,
    }

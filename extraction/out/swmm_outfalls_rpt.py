"""Extract outfall information from SWMM *.rpt files."""

from __future__ import annotations

import pandas as pd

from core.utilities import time_function
from .swmm_rpt_base import _extract_nodes_rpt


@time_function
def extract_swmm_outfalls_rpt(folder_path: str) -> dict:
    """Extract outfall-related data from a SWMM *.rpt file."""
    data = _extract_nodes_rpt(folder_path)
    merged_results = data.get("merged_results", pd.DataFrame())
    outfall_time_series = data.get("node_time_series", pd.DataFrame())

    if not merged_results.empty:
        # Be robust to casing differences (e.g., 'Outfall', 'OUTFALL')
        type_col = "type"
        if type_col in merged_results.columns:
            mask = merged_results[type_col].astype(str).str.strip().str.upper() == "OUTFALL"
            merged_results = merged_results[mask].copy()
        # Collect IDs after filtering (or empty if none matched)
        outfall_ids = merged_results["node_id"].tolist() if "node_id" in merged_results.columns else []
    else:
        outfall_ids = []

    if not outfall_time_series.empty and outfall_ids:
        time_cols = ["time"] if "time" in outfall_time_series.columns else []
        out_cols = [c for c in outfall_time_series.columns if c in outfall_ids]
        outfall_time_series = outfall_time_series[time_cols + out_cols]

    outfall_loading = {k: v for k, v in data.get("outfall_loading", {}).items() if k in outfall_ids}

    return {
        "merged_results": merged_results,
        "outfall_time_series": outfall_time_series,
        "outfall_loading": outfall_loading,
    }

"""Regression tests for SWMM node/outfall time-series retention."""

from __future__ import annotations

import pandas as pd

from extraction.out.swmm_junctions_rpt import extract_swmm_junctions_rpt
from extraction.out.swmm_outfalls_rpt import extract_swmm_outfalls_rpt


def test_junction_extractor_keeps_timeseries_columns_not_in_summary(monkeypatch):
    time_series = pd.DataFrame(
        {
            "time": [0.0, 1.0],
            "A": [1.0, 2.0],
            "I3-PROP_HAMILTON010E": [3.0, 4.0],
        }
    )
    merged = pd.DataFrame(
        {
            "node_id": ["A"],
            "type": ["JUNCTION"],
        }
    )

    def fake_extract_nodes_rpt(_folder):
        return {
            "merged_results": merged,
            "node_time_series": time_series,
            "node_time_series_multi": {"total_inflow": time_series},
            "node_summary": pd.DataFrame(),
            "continuity_errors": {},
            "depth_summary": {},
            "inflow_summary": {},
            "surcharge_summary": {},
            "flooding_summary": {},
        }

    monkeypatch.setattr(
        "extraction.out.swmm_junctions_rpt._extract_nodes_rpt",
        fake_extract_nodes_rpt,
    )

    result = extract_swmm_junctions_rpt("unused")
    assert "I3-PROP_HAMILTON010E" in result["node_time_series"].columns
    assert "I3-PROP_HAMILTON010E" in result["node_time_series_multi"]["total_inflow"].columns


def test_outfall_extractor_keeps_timeseries_columns_not_in_summary(monkeypatch):
    time_series = pd.DataFrame(
        {
            "time": [0.0, 1.0],
            "OUT_A": [1.0, 2.0],
            "OUT_B": [3.0, 4.0],
        }
    )
    merged = pd.DataFrame(
        {
            "node_id": ["OUT_A"],
            "type": ["OUTFALL"],
        }
    )

    def fake_extract_nodes_rpt(_folder):
        return {
            "merged_results": merged,
            "node_time_series": time_series,
            "node_time_series_multi": {"total_inflow": time_series},
            "outfall_loading": {},
        }

    monkeypatch.setattr(
        "extraction.out.swmm_outfalls_rpt._extract_nodes_rpt",
        fake_extract_nodes_rpt,
    )

    result = extract_swmm_outfalls_rpt("unused")
    assert "OUT_B" in result["outfall_time_series"].columns
    assert "OUT_B" in result["outfall_time_series_multi"]["total_inflow"].columns

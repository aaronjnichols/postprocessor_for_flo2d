"""Tests for SWMM multi-series time-series extraction helpers."""

from __future__ import annotations

from extraction.out.swmm_rpt_base import (
    _extract_link_time_series_multi,
    _extract_node_time_series_multi,
)


def test_extract_node_time_series_multi_returns_all_metrics():
    raw_lines = [
        "<<< Node J1 >>>\n",
        "Jan-01-2020 00:00:00 1.0 0.1 2.0 3.0\n",
        "Jan-01-2020 01:00:00 2.0 0.2 2.5 3.2\n",
        "\n",
        "<<< Node J2 >>>\n",
        "Jan-01-2020 00:00:00 4.0 0.3 1.0 4.0\n",
        "Jan-01-2020 01:00:00 5.0 0.4 1.2 4.3\n",
    ]

    result = _extract_node_time_series_multi(raw_lines)

    assert {"total_inflow", "flooding", "depth", "head"} <= set(result.keys())
    inflow = result["total_inflow"]
    depth = result["depth"]
    assert "time" in inflow.columns
    assert "J1" in inflow.columns
    assert "J2" in inflow.columns
    assert list(inflow["J1"]) == [1.0, 2.0]
    assert list(depth["J2"]) == [1.0, 1.2]


def test_extract_link_time_series_multi_returns_all_metrics():
    raw_lines = [
        "<<< Link C1 >>>\n",
        "Jan-01-2020 00:00:00 10.0 5.0 1.0 0.8\n",
        "Jan-01-2020 01:00:00 11.0 5.2 1.2 0.9\n",
        "\n",
    ]

    result = _extract_link_time_series_multi(raw_lines)

    assert {"flow", "velocity", "depth", "capacity"} <= set(result.keys())
    flow = result["flow"]
    velocity = result["velocity"]
    assert "time" in flow.columns
    assert "C1" in flow.columns
    assert list(flow["C1"]) == [10.0, 11.0]
    assert list(velocity["C1"]) == [5.0, 5.2]

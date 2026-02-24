"""Tests for expanded HYCROSS/HYDROSTRUCT time-series parsing."""

from __future__ import annotations

from extraction.out.hycross_out_extraction import extract_hycross_hydrograph_data
from extraction.out.hydrostruct_out_extraction import extract_hydrostruct_out


def test_extract_hycross_hydrograph_data_includes_additional_columns(tmp_path):
    content = """
THE MAXIMUM DISCHARGE FROM CROSS SECTION 1 IS: 10.00 CFS AT TIME: 1.00
MAXIMUM WATER SURFACE ELEVATION AT CROSS SECTION 1 IS: 100.20
HYDROGRAPH AND FLOODPLAIN HYDRAULICS (AVERAGED FOR THE OUTPUT INTERVAL) FOR CROSS SECTION NO:   1
TIME    FLOW WIDTH   AVE. DEPTH       WS ELEV     VELOCITY          DISCHARGE
0.50    10.0         1.0              100.0       2.0               5.0
1.00    11.0         1.2              100.2       2.2               10.0
"""
    file_path = tmp_path / "HYCROSS.OUT"
    file_path.write_text(content, encoding="utf-8")

    hydrograph_data, max_wse_info = extract_hycross_hydrograph_data(str(tmp_path))

    assert 1 in hydrograph_data
    df = hydrograph_data[1]
    assert list(df.columns) == ["time", "flow_width", "ave_depth", "wse", "velocity", "discharge"]
    assert list(df["flow_width"]) == [10.0, 11.0]
    assert list(df["discharge"]) == [5.0, 10.0]
    assert max_wse_info[1] == 100.2


def test_extract_hydrostruct_out_supports_extra_metric_columns(tmp_path):
    content = """
THE MAXIMUM DISCHARGE FOR: S1 STRUCTURE NO. 1 IS: 3.00 AT TIME: 2.00
0.50 1.00 -1.00 0.10
1.00 2.00 -2.00 0.20
2.00 3.00 -3.00 0.30
"""
    file_path = tmp_path / "HYDROSTRUCT.OUT"
    file_path.write_text(content, encoding="utf-8")

    data = extract_hydrostruct_out(str(tmp_path))
    df = data["hydrographs"]["S1"]

    assert list(df.columns) == ["time", "inflow", "outflow", "metric_3"]
    assert list(df["inflow"]) == [1.0, 2.0, 3.0]
    assert list(df["outflow"]) == [-1.0, -2.0, -3.0]
    assert list(df["metric_3"]) == [0.1, 0.2, 0.3]

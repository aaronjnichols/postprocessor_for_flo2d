"""Unit tests for HYCHAN/CHANWS channel output extractors."""

from __future__ import annotations

import math

from extraction.out.chanws_out_extraction import extract_chanws_out
from extraction.out.hychan_out_extraction import extract_hychan_out


def test_extract_hychan_out_parses_multiple_elements(tmp_path):
    content = """
          OUTFLOW HYDROGRAPHS FOR SELECTED CHANNEL ELEMENTS

     CHANNEL HYDROGRAPH FOR ELEMENT NO:  1001
       TIME      ELEV.     THALWEG DEPTH  VELOCITY    DISCHARGE   FROUDE NO.   FLOW AREA    WETTED PERIMETER  HYDRAULIC RADIUS  TOP WIDTH   WIDTH/DEPTH  ENERGY SLOPE  BED SHEAR STRESS  SURFACE AREA
       0.00      10.00         1.00         2.00         3.00      0.10         4.00              5.00             0.80          6.00         7.00       0.010000          0.20000          8.00
       0.25      10.50         1.10         2.10         3.10      0.11         4.10              5.10             0.81          6.10         7.10       0.011000          0.21000          8.10

     CHANNEL HYDROGRAPH FOR ELEMENT NO:  1002
       TIME      ELEV.     THALWEG DEPTH  VELOCITY    DISCHARGE   FROUDE NO.   FLOW AREA    WETTED PERIMETER  HYDRAULIC RADIUS  TOP WIDTH   WIDTH/DEPTH  ENERGY SLOPE  BED SHEAR STRESS  SURFACE AREA
       0.00      20.00         1.20         2.20         3.20      0.12         4.20              5.20             0.82          6.20         7.20       0.012000          0.22000          8.20
"""
    (tmp_path / "HYCHAN.OUT").write_text(content, encoding="utf-8")

    data = extract_hychan_out(str(tmp_path))
    assert sorted(data) == [1001, 1002]
    assert list(data[1001].columns) == [
        "time",
        "elev",
        "depth",
        "velocity",
        "discharge",
        "froude_no",
        "flow_area",
        "wetted_perimeter",
        "hydraulic_radius",
        "top_width",
        "width_depth",
        "energy_slope",
        "bed_shear_stress",
        "surface_area",
    ]
    assert list(data[1001]["time"]) == [0.0, 0.25]
    assert list(data[1002]["discharge"]) == [3.2]


def test_extract_chanws_out_handles_invalid_sentinel(tmp_path):
    content = """
    1001   500000.00  1290000.00  805.1250
    1002   500025.00  1290000.00  -1000.0000
"""
    (tmp_path / "CHANWS.OUT").write_text(content, encoding="utf-8")

    df = extract_chanws_out(str(tmp_path))
    assert list(df["element_id"]) == [1001, 1002]
    assert math.isclose(float(df.loc[df["element_id"] == 1001, "max_wse"].iloc[0]), 805.1250)
    assert math.isnan(float(df.loc[df["element_id"] == 1002, "max_wse"].iloc[0]))

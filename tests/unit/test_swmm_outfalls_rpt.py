import os
import sys

sys.path.append(os.getcwd())

from extraction.out.swmm_outfalls_rpt import extract_swmm_outfalls_rpt


def test_extract_swmm_outfalls_rpt_sections(tmp_path):
    rpt_text = """
******************
Node Summary
******************

Name Type Invert_Elev Max_Depth Ponded_Area
J1 OUTFALL 0.0 10.0 0.0
J2 OUTFALL 1.0 9.0 0.0

******************
Node Depth Summary
******************

Node Type Avg_Depth Max_Depth Max_HGL Time_of_Max_Depth
J1 OUTFALL 2.0 5.0 7.0 0 01:00
J2 OUTFALL 3.0 6.0 8.0 0 02:00

******************
Node Inflow Summary
******************

Node Type Max_Lateral_Inflow Max_Total_Inflow Time_of_Max_Inflow Lateral_Inflow_Volume Total_Inflow_Volume
J1 OUTFALL 1.0 2.0 0 01:00 0.1 0.2
J2 OUTFALL 1.5 2.5 0 02:00 0.15 0.25

******************
Outfall Loading Summary
******************

Outfall_Node Flow_Freq_Pcnt Avg_Flow_CFS Max_Flow_CFS Total_Volume_MG
J1 100.0 0.5 1.0 0.2
J2 50.0 0.25 0.75 0.1
System 75.0 0.4 1.1 0.3

<<< Node J1 >>>
Jan-01-2000 00:00:00 0.0 0 0 0
Jan-01-2000 01:00:00 0.1 0 0 0
<<< Node J2 >>>
Jan-01-2000 00:00:00 0.0 0 0 0
Jan-01-2000 01:00:00 0.2 0 0 0
"""
    rpt_file = tmp_path / "test.rpt"
    rpt_file.write_text(rpt_text)

    data = extract_swmm_outfalls_rpt(str(tmp_path))

    assert not data["node_summary"].empty
    assert not data["node_depth_summary"].empty
    assert not data["node_inflow_summary"].empty
    assert not data["outfall_loading_summary"].empty
    assert not data["outfall_time_series"].empty
    assert set(data["node_summary"]["node_id"]) == {"J1", "J2"}

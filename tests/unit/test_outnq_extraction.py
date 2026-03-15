"""
Unit tests for OUTNQ.OUT extraction normalization.
"""
import os
from pathlib import Path
from uuid import uuid4

import pandas as pd

from core.model_data_extraction import extract_model_data_to_df
from extraction.out.outnq_out_extraction import extract_outnq_out, extract_outnq_summary
from core.constants import GRID_ID, Q_MAX, TIME_PEAK


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / "pytest_workdir"


def _prepare_model_dir(case_name: str) -> str:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    case_dir = TEST_TEMP_ROOT / f"{case_name}_{uuid4().hex}"
    case_dir.mkdir()
    return str(case_dir)


def _write_outnq_file(tmp_dir: str):
    content = """
THE MAX Q AT OUTFLOW ELEMENT:           5 IS:         12.34 CFS AT TIME:          1.50

    ELEMENT TIME (HRS) DISCHARGE (CFS)
        5  0.00  0.00
         0.50  1.00
         1.50 12.34
    """
    path = os.path.join(tmp_dir, 'OUTNQ.OUT')
    with open(path, 'w') as f:
        f.write(content)


def _write_depth_file(tmp_dir: str):
    content = "\n".join([
        "1 100.0 200.0 0.10",
        "5 125.0 225.0 0.75",
    ])
    path = os.path.join(tmp_dir, 'DEPTH.OUT')
    with open(path, 'w') as f:
        f.write(content)


def test_outnq_summary_normalizes_zero_based():
    tmp_dir = _prepare_model_dir("outnq_summary_case")
    _write_outnq_file(tmp_dir)

    df = extract_outnq_summary(tmp_dir)

    assert isinstance(df, pd.DataFrame)
    assert set([GRID_ID, Q_MAX, TIME_PEAK]).issubset(df.columns)
    # Summary grid ids should be integer and 0-based (5 -> 4)
    assert pd.api.types.is_integer_dtype(df[GRID_ID])
    assert (df[GRID_ID] == 4).any()


def test_outnq_timeseries_columns_zero_based():
    tmp_dir = _prepare_model_dir("outnq_timeseries_case")
    _write_outnq_file(tmp_dir)

    result = extract_outnq_out(tmp_dir)
    ts = result['time_series']

    # Columns should include 4 (derived from 1-based 5)
    assert 4 in ts.columns
    # Index should be sorted numeric time
    assert ts.index.is_monotonic_increasing


def test_outnq_summary_uses_canonical_q_max_in_model_merge():
    tmp_dir = _prepare_model_dir("outnq_model_merge_case")
    _write_depth_file(tmp_dir)
    _write_outnq_file(tmp_dir)

    model_df, ancillary = extract_model_data_to_df(tmp_dir, return_ancillary=True)

    assert Q_MAX in model_df.columns
    assert TIME_PEAK in model_df.columns
    assert 'outflow_max_q' not in model_df.columns
    assert model_df.loc[model_df[GRID_ID] == 4, Q_MAX].iat[0] == 12.34
    assert 4 in ancillary['outnq_time_series'].columns


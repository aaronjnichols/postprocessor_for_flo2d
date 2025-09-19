"""
Unit tests for OUTNQ.OUT extraction normalization.
"""
import os
import pandas as pd

from extraction.out.outnq_out_extraction import extract_outnq_out, extract_outnq_summary
from core.constants import GRID_ID, Q_MAX, TIME_PEAK


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


def test_outnq_summary_normalizes_zero_based(tmp_path):
    tmp_dir = str(tmp_path)
    _write_outnq_file(tmp_dir)

    df = extract_outnq_summary(tmp_dir)

    assert isinstance(df, pd.DataFrame)
    assert set([GRID_ID, Q_MAX, TIME_PEAK]).issubset(df.columns)
    # Summary grid ids should be integer and 0-based (5 -> 4)
    assert pd.api.types.is_integer_dtype(df[GRID_ID])
    assert (df[GRID_ID] == 4).any()


def test_outnq_timeseries_columns_zero_based(tmp_path):
    tmp_dir = str(tmp_path)
    _write_outnq_file(tmp_dir)

    result = extract_outnq_out(tmp_dir)
    ts = result['time_series']

    # Columns should include 4 (derived from 1-based 5)
    assert 4 in ts.columns
    # Index should be sorted numeric time
    assert ts.index.is_monotonic_increasing


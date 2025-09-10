"""
Unit tests for DEPCH.OUT and VELOC.OUT dask-optimized readers.
"""
import os
import textwrap

import pandas as pd

from extraction.out.depch_out_extraction import extract_depch_out
from extraction.out.veloc_out_extraction import extract_veloc_out
from core.constants import GRID_ID


def write_simple_out(path: str, filename: str, rows):
    # Each row: (grid, x, y, value)
    lines = [f"{g} {x} {y} {v}" for g, x, y, v in rows]
    with open(os.path.join(path, filename), 'w') as f:
        f.write("\n".join(lines))


def test_depch_reader_normalizes_and_filters(tmp_path):
    rows = [
        (101, 0.0, 0.0, 2.5),
        (102, 0.0, 0.0, 3.0),
    ]
    write_simple_out(tmp_path, 'DEPCH.OUT', rows)

    df = extract_depch_out(str(tmp_path))
    # IDs should be normalized (101 -> 100)
    assert df.iloc[0][GRID_ID] == 100
    assert df.iloc[1][GRID_ID] == 101
    # Column exists
    assert 'channel_depth' in df.columns


def test_veloc_reader_normalizes_and_filters(tmp_path):
    rows = [
        (201, 0.0, 0.0, 1.23),
        (202, 0.0, 0.0, 2.34),
    ]
    write_simple_out(tmp_path, 'VELOC.OUT', rows)

    df = extract_veloc_out(str(tmp_path))
    # IDs should be normalized (201 -> 200)
    assert df.iloc[0][GRID_ID] == 200
    assert df.iloc[1][GRID_ID] == 201
    # Column exists
    assert 'velocity' in df.columns


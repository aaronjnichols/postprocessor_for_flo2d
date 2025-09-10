"""
Unit tests for CHANMAX.OUT extraction including grid-id normalization.
"""
import os
import textwrap

import pandas as pd

from extraction.out.chanmax_out_extraction import extract_chanmax_out
from core.constants import GRID_ID, MAX_STAGE, MAX_DISCHARGE


def write_chanmax(path: str):
    content = textwrap.dedent(
        """

            NODE     MAXIMUM      TIME    MAXIMUM      TIME
                    DISCHARGE    (HRS)     STAGE      (HRS)
                      (CFS)


                  CHANNEL SEGMENT NO:    1
            1001       4.74     13.50     816.53     13.50
            1002       5.00     13.50     815.00     13.50
        """
    ).strip("\n")
    with open(os.path.join(path, 'CHANMAX.OUT'), 'w', encoding='ISO-8859-1') as f:
        f.write(content)


def test_extract_chanmax_normalizes_grid_id(tmp_path):
    write_chanmax(tmp_path)

    df = extract_chanmax_out(str(tmp_path))
    # Expect two rows
    assert len(df) == 2
    # GRID_ID should be 0-based (1001 -> 1000)
    assert df.iloc[0][GRID_ID] == 1000
    assert df.iloc[1][GRID_ID] == 1001
    # Required columns exist
    for col in [GRID_ID, MAX_STAGE, MAX_DISCHARGE]:
        assert col in df.columns


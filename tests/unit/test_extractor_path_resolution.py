"""Regression tests for extractor file-vs-directory path handling."""

from __future__ import annotations

import pandas as pd
import pytest

from extraction.dat.arf_dat_extraction import extract_arf_dat
from extraction.dat.hystruc_dat_extraction import extract_hystruc_results
from extraction.dat.inflow_dat_extraction import extract_inflow_dat
from extraction.dat.mannings_n_dat_extraction import extract_mannings_n_dat
from extraction.dat.outflow_dat_extraction import extract_outflow_dat
from extraction.dat.rain_dat_extraction import extract_rain_dat
from extraction.dat.swmmflort_dat_extraction import extract_swmmflort_dat
from extraction.out.depth_out_extraction import extract_depth_out
from extraction.out.super_out_extraction import extract_super_out


def _assert_frame_equal(left: pd.DataFrame, right: pd.DataFrame) -> None:
    pd.testing.assert_frame_equal(left, right)


def _assert_swmmflort_equal(left: list[dict], right: list[dict]) -> None:
    assert [table["Table"] for table in left] == [table["Table"] for table in right]
    for left_table, right_table in zip(left, right):
        pd.testing.assert_frame_equal(left_table["Data"], right_table["Data"])


@pytest.mark.parametrize(
    ("filename", "extractor", "assert_equal"),
    [
        ("ARF.DAT", extract_arf_dat, _assert_frame_equal),
        ("DEPTH.OUT", extract_depth_out, _assert_frame_equal),
        ("INFLOW.DAT", extract_inflow_dat, _assert_frame_equal),
        ("MANNINGS_N.DAT", extract_mannings_n_dat, _assert_frame_equal),
        ("OUTFLOW.DAT", extract_outflow_dat, _assert_frame_equal),
        ("RAIN.DAT", extract_rain_dat, _assert_frame_equal),
        ("SUPER.OUT", extract_super_out, _assert_frame_equal),
        ("SWMMFLORT.DAT", extract_swmmflort_dat, _assert_swmmflort_equal),
    ],
)
def test_single_file_extractors_accept_directory_or_file_path(
    synthetic_model_dir,
    filename,
    extractor,
    assert_equal,
) -> None:
    """Single-file extractors should treat file and directory inputs identically."""
    directory_result = extractor(str(synthetic_model_dir))
    file_result = extractor(str(synthetic_model_dir / filename))

    assert_equal(file_result, directory_result)


def test_hystruc_extraction_accepts_directory_or_file_path(synthetic_model_dir) -> None:
    """HYSTRUC extraction should resolve either a project directory or HYSTRUC.DAT path."""
    directory_structures, directory_curves = extract_hystruc_results(str(synthetic_model_dir))
    file_structures, file_curves = extract_hystruc_results(str(synthetic_model_dir / "HYSTRUC.DAT"))

    pd.testing.assert_frame_equal(file_structures, directory_structures)
    assert len(file_curves) == len(directory_curves)
    for file_curve, directory_curve in zip(file_curves, directory_curves):
        assert file_curve.keys() == directory_curve.keys()
        assert file_curve["structure_id"] == directory_curve["structure_id"]
        pd.testing.assert_frame_equal(file_curve["Data"], directory_curve["Data"])


def test_extractors_reject_mismatched_existing_file_paths(synthetic_model_dir) -> None:
    """Passing the wrong existing file should fail fast instead of parsing garbage."""
    with pytest.raises(ValueError, match="DEPTH.OUT"):
        extract_depth_out(str(synthetic_model_dir / "OUTFLOW.DAT"))

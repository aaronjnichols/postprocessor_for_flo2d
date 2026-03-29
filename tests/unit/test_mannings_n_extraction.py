"""Regression tests for MANNINGS_N.DAT extraction."""
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

from core.constants import GRID_ID, MANNINGS_N
from core.model_data_extraction import extract_model_data_to_df
from extraction.dat.mannings_n_dat_extraction import extract_mannings_n_dat


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / "pytest_workdir"


def _prepare_model_dir(case_name: str) -> Path:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    model_dir = TEST_TEMP_ROOT / f"{case_name}_{uuid4().hex}"
    model_dir.mkdir()
    return model_dir


def test_extract_mannings_n_from_synthetic_model(synthetic_model_dir) -> None:
    """Extractor should read the grid/x/y/n schema and keep canonical columns."""
    result_df = extract_mannings_n_dat(str(synthetic_model_dir))

    assert isinstance(result_df, pd.DataFrame)
    assert list(result_df.columns) == [GRID_ID, MANNINGS_N]
    assert len(result_df) == 12
    assert result_df[GRID_ID].tolist() == list(range(12))
    assert result_df[MANNINGS_N].tolist()[:5] == pytest.approx([0.035, 0.035, 0.050, 0.050, 0.040])
    assert result_df[MANNINGS_N].iloc[-1] == pytest.approx(0.040)


def test_extract_model_data_merges_mannings_n_by_grid_id() -> None:
    """Merged extraction should align Manning values to normalized grid IDs."""
    model_dir = _prepare_model_dir("mannings_merge")
    (model_dir / "DEPTH.OUT").write_text(
        "1 10.0 20.0 0.50\n"
        "2 11.0 21.0 0.40\n"
        "5 12.0 22.0 0.30\n",
        encoding="utf-8",
    )
    (model_dir / "MANNINGS_N.DAT").write_text(
        "1 662447.71 852480.34 0.035\n"
        "2 662462.71 852480.34 0.050\n"
        "5 662492.71 852465.34 0.040\n",
        encoding="utf-8",
    )

    result_df = extract_model_data_to_df(str(model_dir))

    assert len(result_df) == 3
    assert result_df[GRID_ID].tolist() == [0, 1, 4]
    mannings_by_grid = result_df.set_index(GRID_ID)[MANNINGS_N].to_dict()
    assert mannings_by_grid == pytest.approx({
        0: 0.035,
        1: 0.050,
        4: 0.040,
    })

"""Regression tests for merged model dataframe assembly."""
from pathlib import Path
from uuid import uuid4

import pytest

from core.constants import (
    DEPTH_SUPER,
    GRID_ID,
    MAX_FROUDE_NO,
    NUM_SUPERCRITICAL_TIMESTEPS,
    TIME_SUPER,
)
from core.model_data_extraction import extract_model_data_to_df


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / "pytest_workdir"


def _prepare_model_dir(case_name: str) -> Path:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    model_dir = TEST_TEMP_ROOT / f"{case_name}_{uuid4().hex}"
    model_dir.mkdir()
    return model_dir


def _write_depth_out(model_dir: Path) -> None:
    (model_dir / "DEPTH.OUT").write_text(
        "1 10.0 20.0 0.50\n"
        "5 11.0 21.0 0.70\n",
        encoding="utf-8",
    )


def _write_super_out(model_dir: Path) -> None:
    (model_dir / "SUPER.OUT").write_text(
        "  TOP 1000 SUPERCRITICAL OVERLAND FLOW ELEMENTS IN DESCENDING ORDER OF FROUDE NUMBER\n"
        "          *** NOTE: THIS LIST MAY NOT EXACTLY CORRELATE WITH THE ROUGH.OUT FILE ***\n"
        "                    TO REDUCE THE FROUDE NO: INCREASE FLOODPLAIN n-VALUES OR SHALLOWN FOR LOW FLOWS\n"
        "\n"
        "       NODE    MAX FROUDE NO     DEPTH (FT OR M)     TIME (HR)     NUMBER OF SUPERCRITICAL TIMESTEPS\n"
        "\n"
        "          1         2.43              0.46             11.91                    370\n"
        "          5         2.18              0.61             12.03                    205\n",
        encoding="utf-8",
    )


def test_extract_model_data_merges_super_columns_once() -> None:
    """SUPER.OUT columns should stay canonical after merged extraction."""
    model_dir = _prepare_model_dir("super_merge")
    _write_depth_out(model_dir)
    _write_super_out(model_dir)

    result_df = extract_model_data_to_df(str(model_dir))

    expected_super_columns = {
        MAX_FROUDE_NO,
        DEPTH_SUPER,
        TIME_SUPER,
        NUM_SUPERCRITICAL_TIMESTEPS,
    }

    assert expected_super_columns.issubset(result_df.columns)
    assert not any(column.endswith("_x") or column.endswith("_y") for column in result_df.columns)

    super_by_grid = result_df.set_index(GRID_ID)
    assert super_by_grid.loc[0, MAX_FROUDE_NO] == pytest.approx(2.43)
    assert super_by_grid.loc[0, DEPTH_SUPER] == pytest.approx(0.46)
    assert super_by_grid.loc[4, TIME_SUPER] == pytest.approx(12.03)
    assert super_by_grid.loc[4, NUM_SUPERCRITICAL_TIMESTEPS] == 205


def test_extract_model_data_requires_depth_out() -> None:
    """Merged extraction should fail clearly when DEPTH.OUT is absent."""
    model_dir = _prepare_model_dir("missing_depth")
    _write_super_out(model_dir)

    with pytest.raises(FileNotFoundError, match=r"DEPTH\.OUT"):
        extract_model_data_to_df(str(model_dir))


def test_extract_model_data_rejects_disabled_depth_extractor() -> None:
    """DEPTH.OUT cannot be disabled for merged model extraction."""
    model_dir = _prepare_model_dir("disabled_depth")
    _write_depth_out(model_dir)

    with pytest.raises(ValueError, match=r"DEPTH\.OUT"):
        extract_model_data_to_df(str(model_dir), disable=["DEPTH.OUT"])

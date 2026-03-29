"""
Simple unit tests for ARF.DAT extraction functionality.
"""
from pathlib import Path
from uuid import uuid4

import pytest
import pandas as pd

from core.model_data_extraction import extract_model_data_to_df
from extraction.dat.arf_dat_extraction import extract_arf_dat
from core.constants import GRID_ID, AREA_REDUCTION_FACTOR


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / "pytest_workdir"


def _prepare_model_dir(case_name: str) -> Path:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    model_dir = TEST_TEMP_ROOT / f"{case_name}_{uuid4().hex}"
    model_dir.mkdir()
    return model_dir


class TestARFExtraction:
    """Simple test cases for ARF.DAT file extraction."""
    
    def test_extract_arf_from_synthetic_file(self, arf_file):
        """Test that ARF extraction returns expected DataFrame structure."""
        result_df = extract_arf_dat(str(arf_file))
        
        # Basic structure checks
        assert isinstance(result_df, pd.DataFrame)
        assert list(result_df.columns) == [GRID_ID, AREA_REDUCTION_FACTOR]
        assert len(result_df) > 0
        
        # Data type checks
        assert result_df[GRID_ID].dtype == 'int64'
        assert result_df[AREA_REDUCTION_FACTOR].dtype == 'float64'
        
        # Check that all ARF values are reasonable (0 to 1 for reduction factors)
        assert all(result_df[AREA_REDUCTION_FACTOR] >= 0)
        assert all(result_df[AREA_REDUCTION_FACTOR] <= 1.0)
        
        # Check that grid IDs are positive integers
        assert all(result_df[GRID_ID] >= 0)

    def test_extract_arf_from_model_directory(self, synthetic_model_dir, arf_file):
        """Project-directory inputs should resolve ARF.DAT consistently."""
        file_df = extract_arf_dat(str(arf_file))
        dir_df = extract_arf_dat(str(synthetic_model_dir))

        pd.testing.assert_frame_equal(dir_df, file_df)

    def test_extract_model_data_merges_arf_values(self):
        """Merged model extraction should surface ARF values from a project folder."""
        model_dir = _prepare_model_dir("arf_model")
        (model_dir / "DEPTH.OUT").write_text(
            "1 10.0 20.0 0.5\n"
            "2 11.0 21.0 0.3\n"
            "3 12.0 22.0 0.1\n",
            encoding="utf-8",
        )
        (model_dir / "ARF.DAT").write_text(
            "T 1\n"
            "2 0.25 0 0 0 0 0 0 0 0\n",
            encoding="utf-8",
        )

        result_df = extract_model_data_to_df(str(model_dir))
        arf_by_grid = result_df.set_index(GRID_ID)[AREA_REDUCTION_FACTOR].to_dict()

        assert arf_by_grid == {
            0: 1.0,
            1: 0.25,
            2: 0.0,
        }

    def test_arf_file_not_found(self):
        """Test that missing file raises appropriate error."""
        with pytest.raises(FileNotFoundError):
            extract_arf_dat("nonexistent_file.dat")

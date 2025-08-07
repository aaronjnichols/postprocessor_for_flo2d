"""
Simple unit tests for RAIN.DAT extraction functionality.
"""
import pytest
import pandas as pd

from extraction.dat.rain_dat_extraction import extract_rain_dat
from core.constants import GRID_ID, RAIN_DEPTH


class TestRainExtraction:
    """Simple test cases for RAIN.DAT file extraction."""
    
    def test_extract_rain_from_synthetic_file(self, synthetic_model_dir):
        """Test that rain extraction returns expected DataFrame structure."""
        result_df = extract_rain_dat(str(synthetic_model_dir))
        
        # Basic structure checks
        assert isinstance(result_df, pd.DataFrame)
        assert list(result_df.columns) == [GRID_ID, RAIN_DEPTH]
        assert len(result_df) > 0
        
        # Data type checks  
        assert result_df[GRID_ID].dtype == 'Int64'  # nullable integer
        assert result_df[RAIN_DEPTH].dtype == 'float64'
        
        # Check that rain depths are non-negative
        assert all(result_df[RAIN_DEPTH] >= 0)
        
        # Check that grid IDs are positive integers (excluding any NaN values)
        valid_grid_ids = result_df[GRID_ID].dropna()
        assert all(valid_grid_ids >= 0)
    
    def test_rain_file_not_found(self, tmp_path):
        """Test that missing rain file raises appropriate error."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        with pytest.raises(FileNotFoundError):
            extract_rain_dat(str(empty_dir))
"""
Simple unit tests for ARF.DAT extraction functionality.
"""
import pytest
import pandas as pd

from extraction.dat.arf_dat_extraction import extract_arf_dat
from core.constants import GRID_ID, AREA_REDUCTION_FACTOR


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
    
    def test_arf_file_not_found(self):
        """Test that missing file raises appropriate error."""
        with pytest.raises(FileNotFoundError):
            extract_arf_dat("nonexistent_file.dat")
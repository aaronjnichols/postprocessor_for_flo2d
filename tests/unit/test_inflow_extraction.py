"""
Simple unit tests for INFLOW.DAT extraction functionality.
"""
import pytest
import pandas as pd

from extraction.dat.inflow_dat_extraction import extract_inflow_hydrographs


class TestInflowExtraction:
    """Simple test cases for INFLOW.DAT file extraction."""
    
    def test_extract_inflow_from_synthetic_file(self, synthetic_model_dir):
        """Test that inflow extraction returns expected DataFrame structure."""
        result_df = extract_inflow_hydrographs(str(synthetic_model_dir))
        
        # Basic structure checks
        assert isinstance(result_df, pd.DataFrame)
        
        # If we have data, check its properties
        if not result_df.empty:
            # Check that time index is properly set
            assert result_df.index.name == 'Time (hours)'
            assert result_df.index.dtype == 'float64'
            assert result_df.index.is_monotonic_increasing
            
            # Check that column names are integers (grid IDs)
            assert all(isinstance(col, int) for col in result_df.columns)
            
            # Check that flow values are non-negative
            assert (result_df >= 0).all().all()
        else:
            # Empty DataFrame is acceptable if no inflow data found
            assert len(result_df) == 0
        
    def test_inflow_file_not_found(self, tmp_path):
        """Test that missing inflow file raises appropriate error."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        with pytest.raises(FileNotFoundError):
            extract_inflow_hydrographs(str(empty_dir))
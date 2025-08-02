"""
Simple unit tests for OUTFLOW.DAT extraction functionality.
"""
import pytest
import pandas as pd

from extraction.dat.outflow_dat_extraction import extract_outflow_data
from core.constants import OUTFLOW_CODE, GRID_ID


class TestOutflowExtraction:
    """Simple test cases for OUTFLOW.DAT file extraction."""
    
    def test_extract_outflow_from_synthetic_file(self, synthetic_model_dir):
        """Test that outflow extraction returns expected DataFrame structure."""
        result_df = extract_outflow_data(str(synthetic_model_dir))
        
        # Basic structure checks
        assert isinstance(result_df, pd.DataFrame)
        assert list(result_df.columns) == [OUTFLOW_CODE, GRID_ID]
        
        # If we have data, check its properties
        if not result_df.empty:
            # Check that outflow codes start with 'O'
            assert all(result_df[OUTFLOW_CODE].str.startswith('O'))
            
            # Check that grid IDs are strings (as stored)
            assert result_df[GRID_ID].dtype == 'object'  # pandas string type
            
    def test_outflow_file_not_found(self, tmp_path):
        """Test that missing outflow file raises appropriate error."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        with pytest.raises(FileNotFoundError):
            extract_outflow_data(str(empty_dir))
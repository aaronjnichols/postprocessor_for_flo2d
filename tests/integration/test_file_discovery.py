"""
Integration tests for file discovery and validation.
"""
import pytest
from pathlib import Path

from core.file_discovery import (
    get_file_path, 
    check_file_exists, 
    check_special_processor_requirements,
    get_existing_files,
    get_extractable_files,
)


class TestFileDiscoveryIntegration:
    """Integration tests for file discovery functionality."""
    
    @pytest.mark.integration
    def test_file_discovery_with_synthetic_model(self, synthetic_model_dir):
        """Test file discovery with synthetic model directory."""
        model_path = str(synthetic_model_dir)
        
        # Test individual file discovery
        topo_file = get_file_path(model_path, 'TOPO.DAT')
        assert check_file_exists(topo_file)
        assert Path(topo_file).name == 'TOPO.DAT'
        
        arf_file = get_file_path(model_path, 'ARF.DAT')
        assert check_file_exists(arf_file)
        assert Path(arf_file).name == 'ARF.DAT'
        
        # Test batch file discovery
        existing_files = get_existing_files(model_path)
        
        # Should find our synthetic files
        expected_files = ['TOPO.DAT', 'ARF.DAT', 'RAIN.DAT', 'HYSTRUC.DAT', 
                         'OUTFLOW.DAT', 'DEPTH.OUT', 'SUPER.OUT', 'MANNINGS_N.DAT']
        
        for expected_file in expected_files:
            # Check if file was discovered (key might be the base name)
            found = any(expected_file in path for path in existing_files.values())
            assert found, f"Expected file {expected_file} not found in discovered files"
    
    @pytest.mark.integration  
    def test_file_discovery_missing_files(self, temp_model_dir):
        """Test file discovery behavior with missing files."""
        model_path = str(temp_model_dir)
        
        # Test non-existent file
        missing_file = get_file_path(model_path, 'NONEXISTENT.DAT')
        assert not check_file_exists(missing_file)
        
        # Get existing files from empty directory (most files missing)
        existing_files = get_existing_files(model_path)
        
        # Should handle missing files gracefully
        assert isinstance(existing_files, dict)
        # Some files should be found (from temp_model_dir fixture)
        assert len(existing_files) > 0

    @pytest.mark.integration
    def test_special_processor_requirements_include_hycross_out(self, temp_model_dir):
        """FPXSEC_HYCROSS should require both FPXSEC.DAT and HYCROSS.OUT."""
        model_path = str(temp_model_dir)
        (temp_model_dir / "FPXSEC.DAT").write_text("X 1 0 1\n", encoding="utf-8")

        requirements_met, missing_files = check_special_processor_requirements(model_path, "FPXSEC_HYCROSS")

        assert not requirements_met
        assert missing_files == ["HYCROSS.OUT"]

    @pytest.mark.integration
    def test_discovery_uses_registry_for_hydrostruct_and_levee(self, tmp_path):
        """Central registry additions should be visible through discovery helpers."""
        model_dir = tmp_path / "registry_model"
        model_dir.mkdir()
        (model_dir / "HYDROSTRUCT.OUT").write_text("S 1\n", encoding="utf-8")
        (model_dir / "LEVEE.DAT").write_text("0.0 0\n", encoding="utf-8")

        existing_files = get_existing_files(str(model_dir))
        extractable_files = get_extractable_files(str(model_dir))

        assert "HYDROSTRUCT.OUT" in existing_files
        assert "LEVEE.DAT" in existing_files
        assert "HYDROSTRUCT.OUT" in extractable_files
        assert "LEVEE.DAT" in extractable_files

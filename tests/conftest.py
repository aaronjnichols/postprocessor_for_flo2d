"""
Test configuration and fixtures for the postprocessor test suite.
"""
import pytest
from pathlib import Path


@pytest.fixture
def synthetic_model_dir():
    """Path to the synthetic model files for testing."""
    return Path(__file__).parent / "fixtures" / "synthetic_model"


@pytest.fixture
def error_cases_dir():
    """Path to error case files for testing."""
    return Path(__file__).parent / "fixtures" / "error_cases"


@pytest.fixture 
def arf_file(synthetic_model_dir):
    """Path to ARF.DAT test file."""
    return synthetic_model_dir / "ARF.DAT"


@pytest.fixture
def rain_file(synthetic_model_dir):
    """Path to RAIN.DAT test file."""
    return synthetic_model_dir / "RAIN.DAT"


@pytest.fixture
def chan_file(synthetic_model_dir):
    """Path to CHAN.DAT test file."""
    return synthetic_model_dir / "CHAN.DAT"


@pytest.fixture
def inflow_file(synthetic_model_dir):
    """Path to INFLOW.DAT test file."""
    return synthetic_model_dir / "INFLOW.DAT"


@pytest.fixture
def outflow_file(synthetic_model_dir):
    """Path to OUTFLOW.DAT test file."""
    return synthetic_model_dir / "OUTFLOW.DAT"
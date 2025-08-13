# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FLO-2D hydraulic modeling postprocessor that extracts, analyzes, and visualizes flood simulation data. The system processes FLO-2D model files (.DAT input files and .OUT output files) and generates geospatial outputs (shapefiles, rasters) and analytical reports (Excel, PDF).

## Key Commands

### Development Commands
- **Run tests**: `python run_tests.py` (supports `--unit`, `--integration`, `--coverage`, `--verbose` flags)
- **Run specific test**: `python run_tests.py --file tests/unit/test_module.py`
- **Run main processor**: `python main.py <folder_path> --epsg <code>`
- **Launch GUI**: `python gui\launch_gui.py` or use `scripts\run_gui.bat`

### Testing Commands
- **Unit tests only**: `python run_tests.py --unit`
- **Integration tests**: `python run_tests.py --integration`  
- **With coverage**: `python run_tests.py --coverage`
- **Fast tests (skip slow)**: `python run_tests.py --fast`

### Installation
- **Dependencies**: `pip install -r requirements.txt`
- **Test dependencies**: `pip install -r test-requirements.txt`

## Architecture Overview

### Core Data Flow
```
FLO-2D Files → Extraction → Processing → Output Generation
   *.DAT/OUT → DataFrames → GeoDataFrames → Shapefiles/Rasters/Reports
```

### Module Structure
- **`core/`**: Constants, utilities, and foundational functionality
- **`extraction/`**: File-specific data extractors (organized by `.dat` and `.out` file types)
- **`processing/`**: Data transformation and spatial operations
- **`reporting/`**: Output generation (Excel spreadsheets, PDF charts)
- **`gui/`**: User interface with enhanced messaging system

### Key Architectural Patterns

**Central DataFrame Pattern**: All extracted data converges into a master DataFrame with standardized column names from `core/constants.py`. This prevents naming conflicts and ensures consistency.

**Factory Pattern for Extractors**: Each FLO-2D file type has a dedicated extractor following consistent patterns:
1. File existence check
2. Data extraction using appropriate method (pandas for small files, Dask for large ones)
3. Column standardization using constants
4. Grid ID normalization (FLO-2D uses 1-based, system uses 0-based)
5. Return standardized DataFrame

**Fault-Tolerant Processing**: Missing FLO-2D files are handled gracefully with warnings rather than errors, allowing processing to continue with available data.

## Critical Development Patterns

### Column Names and Constants
ALWAYS use constants from `core/constants.py` for column names:
```python
# ✅ Correct
from core.constants import GRID_ID, DEPTH_MAX, X_COORD, Y_COORD
df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)

# ❌ Wrong  
df['grid_id'] = df['grid_id'] - 1
```

### Grid ID Handling
FLO-2D uses 1-based grid IDs, but the system standardizes on 0-based. Use `normalize_grid_id()`:
```python
from core.constants import normalize_grid_id
df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
```

### File Processing Patterns
All extractors follow this template:
```python
def extract_data(path):
    """Extract data from FLO-2D file."""
    file_path = os.path.join(path, 'FILENAME.EXT')
    
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return pd.DataFrame()
    
    # Use Dask for large files, pandas for small ones
    df = read_with_dask_optimized(file_path, columns=COLUMN_NAMES)
    
    # Standardize column names and grid IDs
    df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
    
    return df
```

### Performance Considerations
- Use `read_with_dask_optimized()` from `extraction/base/extraction_utils.py` for large files
- The system uses ThreadPoolExecutor for parallel raster creation
- Domain vectorization was recently optimized to process only boundary cells instead of all grid cells

### Logging and Timing
The system has sophisticated logging with timing integration:
```python
from core.logger import setup_logger
logger = setup_logger('ModuleName')

# For main processing, use TimingLogger for step tracking
timing_logger = TimingLogger(logger)
timing_logger.log("Step completed")
```

### GUI Integration
The GUI uses an enhanced messaging system with progress tracking. Key components:
- `MessageFormatter`: Translates technical messages to user-friendly ones
- `ProgressTracker`: Manages step-by-step progress indication
- `EnhancedTimingLogger`: Integrates with GUI callbacks for real-time updates

## File Processing Specifics

### Required Files (Core Data)
- `TOPO.DAT`: Topographic elevation (X, Y, elevation format)
- `MANNINGS_N.DAT`: Surface roughness coefficients  
- `DEPTH.OUT`: Maximum flood depths

### Optional Files (Analysis)
- `SUPER.OUT`: Supercritical flow analysis
- `INFLOW.DAT`/`OUTFLOW.DAT`: Boundary conditions
- `HYSTRUC.DAT`: Hydraulic structures
- `CHAN.DAT`: Channel geometry
- Various other `.OUT` files for specialized analysis

### Output Formats
- **Shapefiles/GeoPackages**: Vector outputs with full attribute support
- **GeoTIFF Rasters**: All numerical parameters with optimized cell sizing
- **Excel/PDF Reports**: Analytical outputs with charts and time series

## Testing Framework

The project uses pytest with custom markers:
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests  
- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.data_validation`: Data validation tests

Test fixtures are in `tests/fixtures/synthetic_model/` for consistent testing data.

## Configuration

The system supports configuration through:
- **JSON config**: `config.json` for persistent GUI settings
- **Command line args**: Flexible processing options
- **Style files**: Optional GIS styling for outputs

## Performance Optimizations

Recent optimizations include:
- **Boundary-only domain vectorization**: Processes only boundary cells instead of all grid cells (7x+ speedup for large models)
- **Adaptive algorithm selection**: Automatically chooses optimal processing method based on data size
- **Parallel processing**: Multi-threaded operations where beneficial

## Common Gotchas

1. **Grid ID Conversion**: Always use `normalize_grid_id()` - FLO-2D is 1-based, system is 0-based
2. **Column Names**: Use constants, never hardcode column names
3. **File Paths**: Use `os.path.join()` for cross-platform compatibility
4. **Large Files**: Use Dask utilities for files > 1000 rows
5. **Spatial Data**: Ensure CRS is properly set when creating GeoDataFrames
6. **Error Handling**: Log warnings for missing files, don't crash the pipeline

## Style Guide

Follow the comprehensive style guide in `STYLE_GUIDE.md`. Key points:
- Use `snake_case` for functions and variables
- Use `PascalCase` for classes
- **Helper/private functions**: Prefix with underscore (`_helper_function`)
- Organize imports: standard library → third-party → local
- Include comprehensive docstrings using Google style
- Use descriptive function names that indicate purpose
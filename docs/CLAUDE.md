# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FLO-2D Postprocessor is a Python application that automates the extraction, processing, and visualization of FLO-2D hydraulic modeling data. It processes flood simulation results from various FLO-2D output files and creates geospatial datasets, reports, and visualizations.

## Common Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# For development with test dependencies
pip install -r test-requirements.txt
```

### Running the Application

#### Command Line Interface
```bash
# Process a single project directory
python main.py /path/to/flo2d/project --epsg 2224

# Process multiple directories with custom options
python main.py /path/to/project1 /path/to/project2 --epsg 2223 --verbose --output_format geopackage

# Create FLO-2D points output
python main.py /path/to/project --epsg 2224 --create_flo2d_points

# Apply style files to outputs
python main.py /path/to/project --epsg 2224 --style_folder /path/to/styles
```

#### GUI Application
```bash
# Launch GUI
python gui/launch_gui.py

# Or run GUI directly
python -m gui.flo2d_postprocessor_gui
```

### Testing

#### Using pytest directly
```bash
# Run all tests with coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Run specific test file
pytest tests/unit/test_arf_extraction.py

# Skip slow tests
pytest -m "not slow"
```

#### Using the test runner script
```bash
# Run all tests
python run_tests.py

# Run with specific options
python run_tests.py --unit --coverage --verbose
python run_tests.py --integration --fast
python run_tests.py --file tests/unit/test_domain_vectorization.py
```

### Development Tools
```bash
# Run type checking (if mypy is configured)
mypy .

# Format code (if black/isort are configured)
black .
isort .
```

## Architecture Overview

### Core Processing Pipeline

1. **File Discovery** (`core/file_discovery.py`): Locates FLO-2D input/output files in project directories
2. **Data Extraction** (`extraction/`): Extracts data from various FLO-2D file formats (.DAT, .OUT)
3. **Model Data Consolidation** (`core/model_data_extraction.py`): Merges extracted data into unified DataFrames
4. **Spatial Processing** (`processing/spatial/`): Converts tabular data to geospatial formats (GeoDataFrame)
5. **Vectorization** (`processing/vectorization/`): Creates vector outputs (Shapefiles, GeoPackages)
6. **Rasterization** (`processing/spatial/rasterization.py`): Generates raster outputs (GeoTIFFs)
7. **Reporting** (`reporting/`): Creates Excel spreadsheets and PDF visualizations

### Key Modules

#### Core Components
- `main.py`: Main processing entry point with CLI argument parsing
- `core/constants.py`: Standardized column names and constants used across the codebase
- `core/model_data_extraction.py`: Coordinates parallel extraction from multiple files and merges results

#### Extraction System
The extraction system is organized by file type:
- `extraction/dat/`: Extracts from FLO-2D input files (.DAT format)  
- `extraction/out/`: Extracts from FLO-2D output files (.OUT format)
- `extraction/base/extraction_utils.py`: Common utilities for data extraction and validation

#### Processing Pipeline
- `processing/spatial/geospatial.py`: Coordinate system handling and GeoDataFrame operations
- `processing/vectorization/`: Creates point, line, and polygon vector outputs for different FLO-2D components
- `processing/spatial/rasterization.py`: Converts vector data to raster format using spatial interpolation

### Data Flow Architecture

The application follows a standardized data flow:

1. **Raw File Input**: FLO-2D .DAT and .OUT files
2. **Parallel Extraction**: Multiple extractors run concurrently using ThreadPoolExecutor
3. **Data Standardization**: All extractors return DataFrames with standardized column names from `core/constants.py`
4. **Grid ID Normalization**: Ensures consistent grid identifiers across all datasets using `normalize_grid_id()`
5. **Controlled Merging**: Uses `controlled_merge()` to safely join datasets on `grid_id`
6. **Geospatial Conversion**: Converts to GeoDataFrame with proper CRS
7. **Multi-format Output**: Generates Shapefiles, GeoPackages, GeoTIFFs, Excel files, and PDFs

### GUI Architecture

The GUI (`gui/`) provides a user-friendly interface with:
- `flo2d_postprocessor_gui.py`: Main GUI application using tkinter
- `message_system.py`: Rich messaging system with progress tracking  
- `messaging.py`: Enhanced logging and message routing for GUI integration

### Configuration

- `config.json`: Default configuration for GUI including project paths, EPSG codes, and output preferences
- `pytest.ini`: Test configuration with coverage settings and test markers

## File Type Processors

The application handles these FLO-2D file types:

### Input Files (.DAT)
- **TOPO.DAT**: Grid elevation data
- **MANNINGS_N.DAT**: Surface roughness coefficients  
- **RAIN.DAT**: Rainfall data
- **INFIL.DAT**: Infiltration parameters (Green-Ampt, SCS, Horton)
- **INFLOW.DAT**: Inflow boundary conditions
- **OUTFLOW.DAT**: Outflow boundary locations
- **HYSTRUC.DAT**: Hydraulic structure definitions
- **CHAN.DAT**: Channel geometry and properties
- **SWMM.inp**: SWMM inlet/outlet data
- **FPXSEC.DAT**: Floodplain cross-section data

### Output Files (.OUT)  
- **DEPTH.OUT**: Maximum water depths
- **VELOC.OUT**: Velocity data  
- **MAXWSELEV.OUT**: Maximum water surface elevations
- **SUPER.OUT**: Supercritical flow analysis
- **TIME.OUT**: Time-related hydraulic outputs
- **CHANMAX.OUT**: Channel maximum values
- **HYCROSS.OUT**: Cross-section hydraulic data

## Testing Strategy

Tests are organized with pytest markers:
- `unit`: Fast unit tests for individual functions
- `integration`: Tests that use fixture data files  
- `slow`: Long-running tests
- `data_validation`: Tests that validate data accuracy

Test fixtures are located in `tests/fixtures/synthetic_model/` containing sample FLO-2D files for testing.

## Development Guidelines

### Column Name Standardization
Always use constants from `core/constants.py` instead of hardcoded strings:
```python
# ✅ Good
from core.constants import GRID_ID, TOPO_ELEVATION
df[GRID_ID] = grid_values
df[TOPO_ELEVATION] = elevation_values

# ❌ Bad  
df['grid_id'] = grid_values
df['topo_elevation'] = elevation_values
```

### Error Handling
The codebase uses defensive programming with extensive error handling:
- File existence checks before processing
- DataFrame validation after extraction  
- Graceful degradation when optional files are missing
- Detailed logging of errors and warnings

### Parallel Processing
The application leverages multiprocessing and threading:
- Data extraction uses ThreadPoolExecutor for I/O-bound operations
- Raster creation uses ProcessPoolExecutor for CPU-bound operations
- GUI operations run in separate threads to maintain responsiveness

### Output Formats
Supports multiple output formats:
- **Vector**: Shapefile (.shp) and GeoPackage (.gpkg)
- **Raster**: GeoTIFF (.tif) 
- **Tabular**: Excel (.xlsx), CSV
- **Visualization**: PDF plots and charts
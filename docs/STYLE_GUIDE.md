# FLO-2D Postprocessor Style Guide

## Overview

This style guide establishes comprehensive coding standards for the FLO-2D Postprocessor codebase to ensure consistency, maintainability, and code quality. The codebase is a Python application that processes FLO-2D hydraulic modeling data, extracting, analyzing, and visualizing flood simulation results.

## Project Structure

The codebase follows a modular architecture with clear separation of concerns:

```
postprocessor_for_flo2d/
├── core/                   # Core utilities and constants
├── extraction/             # Data extraction from FLO-2D files
│   ├── base/              # Base extraction utilities
│   ├── dat/               # DAT file extraction modules
│   └── out/               # OUT file extraction modules
├── processing/             # Data processing and spatial operations
│   ├── spatial/           # Geospatial processing
│   └── vectorization/     # Vector data creation
├── reporting/              # Output generation
│   ├── spreadsheets/      # Excel/CSV report generation
│   └── visualization/     # Plotting and visualization
├── gui/                   # GUI components
├── tests/                 # Test modules
└── scripts/               # Utility scripts
```

## Naming Conventions

### Files and Directories

- **Directories**: Use lowercase with underscores (`snake_case`)
  - ✅ `extraction/`, `processing/spatial/`
  - ❌ `Extraction/`, `ProcessingSpatial/`

- **Python Files**: Use lowercase with underscores (`snake_case`) and descriptive names
  - ✅ `rain_dat_extraction.py`, `depth_out_extraction.py`
  - ❌ `RainExtraction.py`, `depthExtraction.py`

### Variables and Functions

- **Variables**: Use lowercase with underscores (`snake_case`)
  ```python
  # ✅ Good
  grid_id = 12345
  max_depth_value = 5.2
  file_path = '/path/to/file.dat'
  
  # ❌ Bad
  gridId = 12345
  MaxDepthValue = 5.2
  FilePath = '/path/to/file.dat'
  ```

- **Functions**: Use lowercase with underscores (`snake_case`) and descriptive verb phrases
  ```python
  # ✅ Good
  def extract_depth_data(file_path):
  def calculate_cell_size(geo_df):
  def create_required_folders(folders):
  
  # ❌ Bad
  def ExtractDepth(file_path):
  def calcCellSize(geo_df):
  def makeFolders(folders):
  ```

- **Helper/Private Functions**: Use leading underscore to indicate internal use
  ```python
  # ✅ Good - Public functions
  def extract_chan_dat(path):
  def process_channel_data(data):
  
  # ✅ Good - Helper/private functions
  def _parse_segment_header(parts):
  def _classify_line_type(line):
  def _validate_channel_geometry(data):
  
  # ❌ Bad - Helper functions without underscore
  def parse_segment_header(parts):  # Should be _parse_segment_header
  def classify_line_type(line):     # Should be _classify_line_type
  ```

- **Constants**: Use UPPERCASE with underscores (`SCREAMING_SNAKE_CASE`)
  ```python
  # ✅ Good
  # Internal 0-based cell identifier
  GRID_ID = 'id'
  # Display 1-based identifier for user-facing outputs
  GRID_ID_DISPLAY = 'grid_id'
  MAX_DEPTH = 'max_depth'
  DEFAULT_EPSG = 4326
  
  # ❌ Bad
  grid_id = 'grid_id'
  maxDepth = 'max_depth'
  defaultEpsg = 4326
  ```

### Classes

- **Class Names**: Use PascalCase
  ```python
  # ✅ Good
  class TimingLogger:
  class FLO2DPostProcessorGUI:
  class RedirectText:
  
  # ❌ Bad
  class timing_logger:
  class flo2d_postprocessor_gui:
  ```

## Import Standards

### Import Order

Follow PEP 8 import ordering with blank lines between groups:

```python
# 1. Standard library imports
import os
import time
import logging
from functools import wraps

# 2. Third-party imports
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point

# 3. Local application imports
from core.constants import GRID_ID, DEPTH_MAX
from core.utilities import time_function
from extraction.base.extraction_utils import read_with_dask_optimized
```

### Import Style

- Use explicit imports from modules when possible
- Import specific functions/classes rather than entire modules when practical
- Use absolute imports relative to project root

```python
# ✅ Good
from core.constants import GRID_ID, X_COORD, Y_COORD
from extraction.base.extraction_utils import read_with_dask_optimized

# ❌ Bad
from core.constants import *
import extraction.base.extraction_utils as utils
```

## Code Organization

### Module Structure

Each module should follow this structure:

```python
"""
Module docstring describing purpose and functionality.

This module handles [specific functionality] for the FLO-2D postprocessor.
"""

# Imports (following import order standards)
import os
import pandas as pd
from core.constants import GRID_ID

# Module-level constants (if any)
DEFAULT_CHUNK_SIZE = 1000

# Functions (in logical order)
def main_function():
    """Primary function with clear docstring."""
    pass

def helper_function():
    """Helper function."""
    pass
```

### Function Organization

- Place main/public functions first
- Follow with helper/private functions
- Group related functions together
- Use descriptive function names that indicate purpose

## Documentation Standards

### Module Docstrings

Use triple quotes for module-level documentation:

```python
"""
Module for extracting rainfall data from FLO-2D RAIN.DAT files.

This module provides functions to parse and extract rainfall distribution
data from FLO-2D model files, applying appropriate multipliers and formatting
the data for further processing.
"""
```

### Function Docstrings

Use Google-style docstrings for functions:

```python
def extract_rain_data(path):
    """
    Extract rainfall data from RAIN.DAT file.
    
    Args:
        path (str): Path to the directory containing RAIN.DAT file.
        
    Returns:
        pd.DataFrame: DataFrame with columns ['grid_id', 'rain_depth'].
        
    Raises:
        FileNotFoundError: If RAIN.DAT file is not found.
        ValueError: If file format is invalid.
    """
```

### Class Docstrings

```python
class TimingLogger:
    """
    A helper class to log the timing of each processing step.
    
    This class provides utilities for tracking execution time of operations
    and logging performance metrics during FLO-2D data processing.
    
    Attributes:
        logger: The logging instance to use for output.
        start_time: Timestamp when logging began.
        last_log_time: Timestamp of the most recent log entry.
    """
```

### Inline Comments

- Use comments sparingly and only when code logic isn't self-evident
- Prefer descriptive variable and function names over comments
- When comments are necessary, explain WHY, not WHAT

```python
# ✅ Good - explains business logic
# Apply FLO-2D's 1-based to 0-based grid ID conversion
df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)

# Ensure grid_id types match before merge to prevent silent failures
super_data[GRID_ID] = super_data[GRID_ID].astype(geo_df[GRID_ID].dtype)

# ❌ Bad - explains obvious code
# Loop through the files
for file in files:
    # Open the file
    with open(file, 'r') as f:
```

## Constants and Configuration

### Constants Module Usage

All column names, file paths, and configuration values must use constants from `core/constants.py`:

```python
# ✅ Good
from core.constants import GRID_ID, DEPTH_MAX, X_COORD, Y_COORD

def extract_depth_data(file_path):
    # GRID_ID is the internal 0-based id
    df = pd.read_csv(file_path, names=[GRID_ID, X_COORD, Y_COORD, DEPTH_MAX])
    return df

# ❌ Bad
def extract_depth_data(file_path):
    df = pd.read_csv(file_path, names=['grid_id', 'x', 'y', 'depth_max'])
    return df
```

### Column Name Standardization

- Always use constants for column names
- Use the `normalize_grid_id()` function for grid ID conversion
- Use `standardize_grid_id_column()` when working with legacy data

```python
# ✅ Good
from core.constants import GRID_ID, normalize_grid_id

df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)

# For user-facing outputs, add a 1-based display column
df['grid_id'] = df[GRID_ID] + 1

## SWMM Output Schema (Vector Layers)

SWMM vector outputs use short, Shapefile-safe field names (≤ 10 chars) and deduplicate
overlapping INP vs RPT data. INP “design” fields are preferred; RPT provides “observed” metrics.

### Junctions (Nodes)
- name: SWMM node name
- j_type: node type from RPT Node Summary
- z_inv: invert elevation (INP)
- dmax_cap: maximum depth capacity (INP)
- dinit: initial depth (INP)
- dsurch: surcharge depth (INP)
- pond_area: ponded area (INP)
- cont_err: continuity error percent (RPT)
- avg_dep: average depth (RPT)
- dmax_obs: maximum observed depth (RPT)
- max_hgl: maximum head (RPT)
- t_max_dep: time of maximum depth (RPT)
- lat_inflw: maximum lateral inflow (RPT)
- tot_inflw: maximum total inflow (RPT)
- t_max_inf: time of maximum inflow (RPT)
- latinflvol: lateral inflow volume (RPT)
- totinflvol: total inflow volume (RPT)
- hrs_surch: hours surcharged (RPT)
- h_abv_crwn: max height above crown (RPT)
- d_blw_rim: min depth below rim (RPT)
- hr_flooded: hours flooded (RPT)
- flood_rate: max flooding rate (RPT)
- t_flood: time of max flooding (RPT)
- flood_vol: total flood volume (RPT)
- ponded_dep: max ponded depth (RPT)

### Outfalls
- name: SWMM outfall name
- o_type: outfall type (INP)
- z_inv: invert elevation (INP)
- stage: stage data (INP, if present)
- tide_gate: tide gate setting (INP)
- flwfrqpcnt: flow frequency percent (RPT)
- avg_flow: average flow (RPT)
- max_flow: maximum flow (RPT)
- tot_vol_mg: total volume in MG (RPT)

### Links (Conduits)
- name: conduit ID
- l_type: link type (RPT classification)
- from: from-node name (INP)
- to: to-node name (INP)
- len: length (INP)
- n: Manning’s n (INP)
- in_off: inlet offset (INP)
- out_off: outlet offset (INP)
- q_init: initial flow (INP)
- qmax_inp: max flow from INP (INP)
- max_flow: maximum flow (RPT)
- day_max: day of maximum flow (RPT)
- time_max: time of maximum flow (RPT)
- max_vel: maximum velocity (RPT)
- flow_ratio: flow ratio (RPT)
- depth_rat: depth ratio (RPT)
- hrs_full, hrs_full_u, hrs_full_d: hours at full/full-upstream/downstream (RPT)
- hrs_above: hours above full normal depth (RPT)
- hrs_cap: hours at capacity (RPT)
- adj_len: adjusted length (RPT)
- dry_up, dry_down, dry_sub, dry_sup: dryness indicators (RPT)
- crit_up, crit_down: critical flow flags (RPT)
- froude: Froude number (RPT)
- flow_chg: flow change indicator (RPT)

Notes:
- Names are always ≤ 10 characters to remain Shapefile-safe.
- INP design fields win when semantics overlap; RPT observed fields are kept under different names.

# ❌ Bad
df['grid_id'] = df['grid_id'] - 1
```

## Error Handling

### Exception Handling Patterns

Use specific exception handling with informative messages:

```python
# ✅ Good
try:
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except IOError as e:
    logger.warning(f"Unable to create log file at {log_file}. "
                  f"Logging will continue on console only. Error: {e}")

# ❌ Bad
try:
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except:
    pass
```

### Error Message Standards

- Include context about what operation failed
- Include the specific error details
- Provide guidance on potential solutions when possible
- Use logger instead of print for error messages

```python
# ✅ Good
logger.error(f"Failed to create SUPER.OUT Points {output_format}: {str(e)}")
logger.warning(f"ARF file not found at {arf_file}. Skipping ARF extraction.")

# ❌ Bad
print("Error")
print(f"Error: {e}")
```

## Logging Standards

### Logger Setup

Use the centralized logging setup from `core/logger.py`:

```python
from core.logger import setup_logger

logger = setup_logger('ModuleName', level=logging.INFO)
```

### Logging Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General information about program execution
- **WARNING**: Something unexpected happened, but the program can continue
- **ERROR**: A serious problem occurred, but the program can continue
- **CRITICAL**: A very serious error occurred, program may not be able to continue

```python
# ✅ Good usage
logger.info("Starting data extraction from DEPTH.OUT")
logger.warning(f"ARF file not found at {arf_file}. Skipping ARF extraction.")
logger.error(f"Failed to create raster for column '{column}'. Error: {e}")

# ❌ Bad usage
print("Starting data extraction")
logger.info(f"Error: {e}")  # Should be logger.error
```

### Timing Logs

Use TimingLogger for performance monitoring:

```python
from core.logger import TimingLogger

timing_logger = TimingLogger(logger)
timing_logger.log("Data extraction completed")
timing_logger.log("Raster creation finished")
```

## Data Processing Standards

### DataFrame Operations

- Always use constants for column names
- Check for required columns before operations
- Handle missing data gracefully
- Use descriptive variable names for intermediate results

```python
# ✅ Good
def process_super_data(geo_df, super_data):
    """Process SUPER.OUT data and merge with main DataFrame."""
    # Ensure consistent data types for merge
    super_data[GRID_ID] = super_data[GRID_ID].astype(geo_df[GRID_ID].dtype)
    
    # Merge with explicit suffixes to avoid conflicts
    merged_df = geo_df.merge(super_data, on=GRID_ID, how='left', suffixes=('_orig', ''))
    
    # Filter to rows with valid super data
    valid_super_df = merged_df.dropna(subset=[MAX_FROUDE_NO, DEPTH_SUPER])
    
    return valid_super_df

# ❌ Bad
def process_super(df1, df2):
    df2['grid_id'] = df2['grid_id'].astype(df1['grid_id'].dtype)
    result = df1.merge(df2, on='grid_id', how='left')
    result = result.dropna(subset=['max_froude_no', 'depth_super'])
    return result
```

### File I/O Operations

- Use context managers for file operations
- Check file existence before processing
- Provide informative error messages
- Use absolute paths when possible

```python
# ✅ Good
def extract_rain_data(path):
    """Extract rainfall data from RAIN.DAT file."""
    rain_file = os.path.join(path, 'RAIN.DAT')
    
    if not os.path.exists(rain_file):
        raise FileNotFoundError(f"RAIN.DAT file not found at {rain_file}")
    
    try:
        with open(rain_file, 'r') as file:
            lines = file.readlines()
    except IOError as e:
        raise IOError(f"Failed to read RAIN.DAT file: {e}")
    
    # Process data...
    return df

# ❌ Bad
def extract_rain_data(path):
    file = open(path + '/RAIN.DAT', 'r')
    lines = file.readlines()
    file.close()
    # Process data...
    return df
```

## Performance Considerations

### Large File Handling

Use Dask for large files and implement chunking:

```python
# ✅ Good for large files
from extraction.base.extraction_utils import read_with_dask_optimized

def extract_large_file(file_path):
    """Extract data from large FLO-2D output file."""
    column_names = [GRID_ID, X_COORD, Y_COORD, DEPTH_MAX]
    df = read_with_dask_optimized(file_path, column_names=column_names).compute()
    return df

# ✅ Good for small files
def extract_small_file(file_path):
    """Extract data from small FLO-2D input file."""
    df = pd.read_csv(file_path, delim_whitespace=True, header=None, 
                     names=[GRID_ID, RAIN_DEPTH])
    return df
```

### Memory Management

- Use appropriate data types
- Remove unnecessary intermediate variables
- Use chunked processing for large datasets

```python
# ✅ Good
df[GRID_ID] = pd.to_numeric(df[GRID_ID], errors='coerce').astype('Int64')
df[RAIN_DEPTH] = pd.to_numeric(df[RAIN_DEPTH], errors='coerce').astype('float32')

# ❌ Bad - uses default float64 unnecessarily
df[RAIN_DEPTH] = pd.to_numeric(df[RAIN_DEPTH], errors='coerce')
```

## Testing Standards

### Test File Organization

- Place tests in `tests/` directory
- Use descriptive test file names: `test_module_name.py`
- Group related tests in test classes

### Test Function Naming

Use descriptive test function names that explain what is being tested:

```python
# ✅ Good
def test_extract_rain_data_with_valid_file():
def test_normalize_grid_id_converts_one_based_to_zero_based():
def test_merge_fails_gracefully_with_missing_columns():

# ❌ Bad
def test_rain():
def test_grid_id():
def test_merge():
```

## GUI Standards

### Widget Organization

- Use descriptive variable names for widgets
- Group related widgets logically
- Implement consistent styling

```python
# ✅ Good
class FLO2DPostProcessorGUI:
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.master, padding="15")
        
        # Input section
        folders_label = ttk.Label(main_frame, text="FLO-2D Folders:")
        folders_entry = ttk.Entry(main_frame, width=50)
        browse_button = ttk.Button(main_frame, text="Browse", command=self.browse_folders)
```

### Event Handling

Use descriptive method names for event handlers:

```python
# ✅ Good
def on_browse_button_clicked(self):
def on_process_complete(self):
def on_window_closing(self):

# ❌ Bad
def handle_click(self):
def callback(self):
def event_handler(self):
```

## Code Quality Guidelines

### Function Length

- Keep functions focused and under 50 lines when possible
- Extract complex logic into separate helper functions
- Use meaningful function names that describe their purpose

### Complexity Management

- Avoid deeply nested conditionals (max 3 levels)
- Use early returns to reduce nesting
- Extract complex conditions into well-named variables

```python
# ✅ Good
def process_file(file_path):
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return None
    
    if not file_path.endswith('.DAT'):
        logger.warning(f"Invalid file type: {file_path}")
        return None
    
    # Process file...
    return result

# ❌ Bad
def process_file(file_path):
    if os.path.exists(file_path):
        if file_path.endswith('.DAT'):
            # Process file...
            return result
        else:
            logger.warning(f"Invalid file type: {file_path}")
            return None
    else:
        logger.warning(f"File not found: {file_path}")
        return None
```

## Version Control Standards

### Commit Messages

Use descriptive commit messages that explain the change:

```
# ✅ Good
Add rainfall data extraction with multiplier support
Fix grid ID column standardization in channel modules
Refactor error handling in file processing utilities

# ❌ Bad
Fix bug
Update code
Changes
```

### File Organization

- Keep related changes in single commits
- Avoid mixing refactoring with feature additions
- Test changes before committing

## Dependencies and Requirements

### External Libraries

Current approved dependencies (from `requirements.txt`):
- `pandas` - Data manipulation and analysis
- `numpy` - Numerical computing
- `geopandas` - Geospatial data handling
- `shapely` - Geometric operations
- `rasterio` - Raster data I/O
- `matplotlib` - Plotting and visualization
- `openpyxl` - Excel file operations
- `xlsxwriter` - Excel file writing
- `psutil` - System and process utilities
- `ttkthemes` - GUI theming
- `dask[dataframe]` - Parallel computing
- `dask-geopandas` - Geospatial parallel computing

### Adding New Dependencies

- Justify new dependencies in code reviews
- Ensure compatibility with existing dependencies
- Update `requirements.txt` when adding new libraries
- Consider licensing implications

## Conclusion

This style guide ensures consistency across the FLO-2D Postprocessor codebase while maintaining flexibility for future enhancements. All developers should follow these guidelines to maintain code quality and facilitate collaboration.

For questions about style decisions not covered in this guide, refer to:
1. PEP 8 (Python Style Guide)
2. Google Python Style Guide
3. Project maintainer guidance

Regular reviews of this style guide will ensure it remains current with project needs and Python best practices.

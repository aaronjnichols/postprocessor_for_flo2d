# FLO-2D Postprocessor

A Python application for automated extraction, processing, and visualization of FLO-2D hydraulic modeling data. Convert FLO-2D simulation results into geospatial datasets, Excel reports, and PDF visualizations.

## Features

- Automated data extraction from major FLO-2D input (.DAT) and output (.OUT) files
- Geospatial outputs: Shapefiles and GeoPackages for GIS analysis
- Raster generation: GeoTIFFs for depth, velocity, and other parameters
- Excel reports: Structured workbooks with charts for channels, cross sections, hydraulic structures, SWMM, etc.
- PDF reports: Cross section plots, hydrographs, rating curves (4-per-page layout)
- GUI and CLI: Launch via tkinter GUI or command-line
- Batch processing: Process multiple projects in one run

## Quick Start

This project is distributed as source code. Set up a Python environment locally and use the helper scripts under `scripts/` when you are on Windows.

### Windows helpers
- `scripts\setup.bat` creates a virtual environment and installs dependencies
- `scripts\run_gui.bat` launches the GUI inside that environment

### Manual install (Windows/macOS/Linux)
```bash
# Clone the repository
git clone https://github.com/yourusername/postprocessor_for_flo2d.git
cd postprocessor_for_flo2d

# Install dependencies
pip install -r requirements.txt
# Optional: install test dependencies
pip install -r test-requirements.txt

# Launch GUI
python gui/launch_gui.py

# Or run from command line
python main.py /path/to/your/flo2d/project --epsg 2224
```

## Usage

### GUI workflow
1. Select the FLO-2D project folder
2. Set the coordinate system EPSG code
3. Configure output options (GeoPackage vs. Shapefile, FLO-2D points, styles)
4. Run processing and review the generated outputs

### Command line interface
```bash
# Process a single project
python main.py /path/to/flo2d/project --epsg 2224

# Process multiple projects with custom options
python main.py project1/ project2/ --epsg 2223 --verbose --output_format geopackage

# Create FLO-2D points output
python main.py /path/to/project --epsg 2224 --create_flo2d_points

# Apply custom style files
python main.py /path/to/project --epsg 2224 --style_folder /path/to/qml/styles
```

## Supported File Types

### Input files (.DAT)
- TOPO.DAT: Grid elevation data
- MANNINGS_N.DAT: Surface roughness coefficients
- RAIN.DAT: Rainfall data and time series
- INFIL.DAT: Infiltration parameters (Green-Ampt, SCS, Horton)
- INFLOW.DAT: Inflow boundary conditions
- OUTFLOW.DAT: Outflow boundary locations
- HYSTRUC.DAT: Hydraulic structure definitions
- CHAN.DAT: Channel geometry and properties
- SWMM.inp: SWMM inlet/outlet data
- FPXSEC.DAT: Floodplain cross-section data

### Output files (.OUT)
- DEPTH.OUT: Maximum water depths
- VELOC.OUT: Velocity magnitude and direction
- MAXWSELEV.OUT: Maximum water surface elevations
- SUPER.OUT: Supercritical flow analysis
- TIME.OUT: Time-related hydraulic parameters
- CHANMAX.OUT: Channel maximum flow values
- HYCROSS.OUT: Floodplain cross-section hydraulic data
- HYDROSTRUCT.OUT: Hydraulic structure performance

## Output Products

### Geospatial data
- Vector: Shapefile (.shp) or GeoPackage (.gpkg)
- Raster: GeoTIFF (.tif) for depth, velocity, elevation, etc.

### Reports and visualizations
- Excel workbooks with charts and summaries
- PDF visualizations (4 plots per page) for cross sections, hydrographs, rating curves

### Key outputs include
- Computational domain boundary
- Maximum flood depth rasters
- Velocity magnitude and direction
- Water surface elevation maps
- Inflow/outflow node locations
- Channel cross-sections and bank segments
- Hydraulic structure locations and performance
- SWMM nodes, links, outfalls
- Floodplain cross-section lines

## Configuration

### GUI configuration
Settings persist in `config.json`. You can edit this file directly:

```json
{
  "flo2d_folders": [
    "C:/Users/Public/Documents/FLO2D_Projects/Sample_Project"
  ],
  "epsg_number": "2224",
  "create_flo2d_points": true,
  "style_folder": "",
  "output_format": "GeoPackage"
}
```

### Command line options
```bash
python main.py --help
```

## Development

### Running tests
```bash
# Install test dependencies
pip install -r test-requirements.txt

# Run all tests (with coverage per pytest.ini)
pytest

# Run specific test selections
pytest tests/unit -q
pytest tests/integration -q
```

### Project structure
```
postprocessor_for_flo2d/
  core/         # Core utilities and constants
  extraction/   # Data extraction from FLO-2D files
  processing/   # Spatial processing and vectorization
  reporting/    # Report and visualization generation
  gui/          # Graphical user interface
  tests/        # Test suite
  scripts/      # Setup and launchers
  docs/         # Developer docs (style guide)
```

## Troubleshooting

"No FLO-2D files found"
- Ensure the folder contains FLO-2D .DAT and .OUT files
- Check file names follow expected FLO-2D conventions

"Coordinate system error"
- Verify the EPSG code matches the model's coordinate system
- Common codes: 2224 (NAD83 State Plane), 4326 (WGS84), 3857 (Web Mercator)

"Missing dependencies"
- Run `pip install -r requirements.txt`

## Documentation

- Coding standards live in `docs/STYLE_GUIDE.md`
- Example configuration: `config.example.json`

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE).

## Version History

See [CHANGELOG.md](CHANGELOG.md) for updates (currently a placeholder until the first release).

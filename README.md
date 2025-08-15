# FLO-2D Postprocessor

A comprehensive Python application for automated extraction, processing, and visualization of FLO-2D hydraulic modeling data. Convert your FLO-2D flood simulation results into geospatial datasets, Excel reports, and visualizations with ease.

## ✨ Features

- **Automated Data Extraction**: Processes all major FLO-2D input (.DAT) and output (.OUT) files
- **Geospatial Output**: Creates Shapefiles and GeoPackages for GIS analysis
- **Raster Generation**: Generates GeoTIFF rasters for depth, velocity, and other flood parameters
- **Excel Reports**: Automated spreadsheets with charts for hydraulic structures, channels, and time series data
- **User-Friendly GUI**: Easy-to-use graphical interface for non-programmers
- **Batch Processing**: Process multiple FLO-2D projects simultaneously
- **Multi-format Support**: Outputs in Shapefile, GeoPackage, GeoTIFF, Excel, and PDF formats

## 🚀 Quick Start

### Option 1: Download Executable (Recommended for Non-Programmers)

1. Download the latest `FLO2D-Postprocessor-Setup.exe` from the [Releases](../../releases) page
2. Run the installer and follow the setup wizard
3. Launch "FLO-2D Postprocessor" from your desktop or Start Menu
4. Use the GUI to select your FLO-2D project folder and configure settings

### Option 2: Python Installation (For Developers)

#### Prerequisites
- Python 3.8 or higher
- Windows, macOS, or Linux

#### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/postprocessor_for_flo2d.git
cd postprocessor_for_flo2d

# Install dependencies
pip install -r requirements.txt

# Launch GUI
python gui/launch_gui.py

# Or run from command line
python main.py /path/to/your/flo2d/project --epsg 2224
```

## 📖 Usage

### GUI Interface
1. **Select FLO-2D Project Folder**: Choose the directory containing your FLO-2D files
2. **Set Coordinate System**: Enter the EPSG code for your project (e.g., 2224 for NAD83 State Plane)
3. **Configure Output Options**: Choose output formats and optional features
4. **Run Processing**: Click "Run" to start the automated processing

### Command Line Interface
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

## 📁 Supported File Types

### Input Files (.DAT)
- **TOPO.DAT**: Grid elevation data
- **MANNINGS_N.DAT**: Surface roughness coefficients
- **RAIN.DAT**: Rainfall data and time series
- **INFIL.DAT**: Infiltration parameters (Green-Ampt, SCS, Horton)
- **INFLOW.DAT**: Inflow boundary conditions
- **OUTFLOW.DAT**: Outflow boundary locations
- **HYSTRUC.DAT**: Hydraulic structure definitions
- **CHAN.DAT**: Channel geometry and properties
- **SWMM.inp**: SWMM inlet/outlet data
- **FPXSEC.DAT**: Floodplain cross-section data

### Output Files (.OUT)
- **DEPTH.OUT**: Maximum water depths
- **VELOC.OUT**: Velocity magnitude and direction
- **MAXWSELEV.OUT**: Maximum water surface elevations
- **SUPER.OUT**: Supercritical flow analysis
- **TIME.OUT**: Time-related hydraulic parameters
- **CHANMAX.OUT**: Channel maximum flow values
- **HYCROSS.OUT**: Cross-section hydraulic data
- **HYDROSTRUCT.OUT**: Hydraulic structure performance
- And many more...

## 📊 Output Products

The postprocessor generates comprehensive outputs in multiple formats:

### Geospatial Data
- **Vector Data**: Points, lines, and polygons in Shapefile (.shp) or GeoPackage (.gpkg) format
- **Raster Data**: GeoTIFF (.tif) files for depth, velocity, elevation, and other parameters
- **Coordinate Systems**: Proper CRS assignment for GIS integration

### Reports and Visualizations
- **Excel Spreadsheets**: Detailed tabular data with embedded charts
- **PDF Reports**: Cross-section plots, rating curves, and hydrographs
- **Time Series Data**: Hydrographs for inflows, outflows, and hydraulic structures

### Key Outputs Include
- Computational domain boundary
- Maximum flood depth rasters
- Velocity magnitude and direction
- Water surface elevation maps
- Inflow/outflow node locations
- Channel cross-sections and bank segments  
- Hydraulic structure locations and performance
- SWMM inlet/outlet locations
- Floodplain cross-section lines

## ⚙️ Configuration

### GUI Configuration
Settings are automatically saved in `config.json`. You can also manually edit this file:

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

### Command Line Options
```bash
python main.py --help
```

## 🔧 Development

### Running Tests
```bash
# Install test dependencies
pip install -r test-requirements.txt

# Run all tests
python run_tests.py

# Run specific test types
python run_tests.py --unit --coverage
python run_tests.py --integration
```

### Project Structure
```
postprocessor_for_flo2d/
├── core/                   # Core utilities and constants
├── extraction/             # Data extraction from FLO-2D files
├── processing/             # Spatial processing and vectorization
├── reporting/              # Report and visualization generation
├── gui/                   # Graphical user interface
├── tools/                 # Build scripts and utilities
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## 🐛 Troubleshooting

### Common Issues

**"No FLO-2D files found"**
- Ensure your folder contains FLO-2D files (.DAT and .OUT files)
- Check that file names match the expected FLO-2D naming convention

**"Coordinate system error"**
- Verify the EPSG code matches your FLO-2D model's coordinate system
- Common codes: 2224 (NAD83), 4326 (WGS84), 3857 (Web Mercator)

**"Missing dependencies"**
- For executable: Reinstall using the setup program
- For Python: Run `pip install -r requirements.txt`

### Getting Help
- Check the [Issues](../../issues) page for known problems
- Review the documentation in the `docs/` folder
- Ensure your FLO-2D files are valid and complete

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the FLO-2D hydraulic modeling community
- Utilizes powerful Python geospatial libraries (GeoPandas, Rasterio, Shapely)
- GUI built with tkinter for cross-platform compatibility

## 📈 Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and updates.

---

**Note**: This software is provided as-is for use with FLO-2D hydraulic models. It is not affiliated with or endorsed by FLO-2D Software, Inc.
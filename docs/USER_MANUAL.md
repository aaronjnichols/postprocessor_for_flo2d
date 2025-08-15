# FLO-2D Postprocessor User Manual

## Table of Contents
1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Using the GUI](#using-the-gui)
4. [Command Line Usage](#command-line-usage)
5. [Understanding Outputs](#understanding-outputs)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Features](#advanced-features)

## Getting Started

### What is the FLO-2D Postprocessor?

The FLO-2D Postprocessor is a comprehensive tool that automatically processes FLO-2D hydraulic modeling results. It takes the various output files from your FLO-2D simulations and converts them into useful geospatial data, spreadsheets, and visualizations that you can use for analysis, reporting, and presentation.

### What You Need

**For FLO-2D Data:**
- A completed FLO-2D model run with output files
- Knowledge of your model's coordinate system (EPSG code)

**System Requirements:**
- Windows 10 or later (recommended)
- 4 GB RAM minimum, 8 GB recommended
- 1 GB free disk space
- For large models: 16 GB+ RAM recommended

## Installation

### Method 1: Executable Installer (Recommended)

1. **Download** the latest `FLO2D-Postprocessor-Setup.exe` from the releases page
2. **Run** the installer as administrator
3. **Follow** the installation wizard
4. **Launch** from desktop shortcut or Start Menu

### Method 2: Python Installation (For Developers)

```bash
# Download source code
git clone https://github.com/yourusername/postprocessor_for_flo2d.git
cd postprocessor_for_flo2d

# Install Python dependencies
pip install -r requirements.txt

# Launch GUI
python gui/launch_gui.py
```

## Using the GUI

### Main Interface Overview

When you launch the application, you'll see the main window with several sections:

1. **Project Configuration** (top section)
2. **Processing Options** (middle section)  
3. **Output Display** (bottom section)
4. **Control Buttons** (Run, Clear, Settings)

### Step-by-Step Workflow

#### Step 1: Select Your FLO-2D Project

1. **Click** "Browse" next to "FLO-2D Project Folders"
2. **Navigate** to your FLO-2D model directory
3. **Select** the folder containing your .DAT and .OUT files
4. **Click** "OK"

**What to look for:** Your folder should contain files like:
- TOPO.DAT, DEPTH.OUT, VELOC.OUT (essential files)
- CHAN.DAT, HYSTRUC.DAT (if you have channels/structures)
- RAIN.DAT, INFLOW.DAT (if applicable to your model)

#### Step 2: Set Coordinate System

1. **Enter** your EPSG code in the "EPSG Number" field
2. **Common codes:**
   - `2224` - NAD83 State Plane (common in US)
   - `4326` - WGS84 Geographic (lat/lon)
   - `3857` - Web Mercator (for web maps)

**How to find your EPSG code:**
- Check your FLO-2D model documentation
- Look at existing GIS files from your project
- Use [epsg.io](https://epsg.io) to search by location
- When in doubt, ask your GIS specialist

#### Step 3: Configure Output Options

**Output Format:**
- **GeoPackage** (recommended): Single file, better performance
- **Shapefile**: Multiple files, widely compatible

**Create FLO-2D Points:**
- ✅ Check to create point data with flow directions
- Useful for detailed analysis in GIS software

**Style Folder (optional):**
- Path to QGIS style files (.qml)
- Leave blank if you don't have custom styles

#### Step 4: Run Processing

1. **Click** "Run" (or press Ctrl+R or F5)
2. **Monitor** progress in the output window
3. **Wait** for "Processing completed successfully" message
4. **Check** the output folders for results

### Understanding the Progress Display

The GUI shows detailed progress information:
- **File discovery:** Finding FLO-2D files in your project
- **Data extraction:** Reading data from each file
- **Spatial processing:** Converting to geospatial formats
- **Output creation:** Generating final files

**Typical processing times:**
- Small model (< 10,000 cells): 1-2 minutes
- Medium model (10,000-50,000 cells): 2-10 minutes  
- Large model (> 50,000 cells): 10+ minutes

## Command Line Usage

For advanced users and batch processing:

### Basic Usage
```bash
# Process a single project
python main.py "C:\FLO2D_Projects\MyProject" --epsg 2224

# Process multiple projects
python main.py "C:\Projects\Project1" "C:\Projects\Project2" --epsg 2224
```

### Advanced Options
```bash
# Verbose output with GeoPackage format
python main.py "C:\MyProject" --epsg 2224 --verbose --output_format geopackage

# Create FLO-2D points and apply styles
python main.py "C:\MyProject" --epsg 2224 --create_flo2d_points --style_folder "C:\Styles"

# Get help
python main.py --help
```

## Understanding Outputs

After processing, you'll find three new folders in your project directory:

### flo2d_rasters/
**GeoTIFF raster files (.tif)** for spatial analysis and mapping:
- `depth_max.tif` - Maximum flood depths
- `velocity.tif` - Flow velocities  
- `wse_max.tif` - Water surface elevations
- `topo.tif` - Ground elevation
- `mannings_n.tif` - Surface roughness

**Use for:** Flood mapping, depth analysis, velocity analysis, creating maps

### flo2d_shp/
**Vector data files** (Shapefile .shp or GeoPackage .gpkg):
- `computational_domain` - Model boundary
- `inflow_points` - Inflow locations
- `outflow_points` - Outflow locations
- `hystruc_points` - Hydraulic structures
- `channel_xsec_lines` - Channel cross-sections
- `swmm_inlets` - SWMM inlet locations

**Use for:** GIS analysis, creating maps with specific features, spatial queries

### flo2d_plots/
**Reports and visualizations:**
- `*.xlsx` - Excel spreadsheets with data tables and charts
- `*.pdf` - PDF plots for channels, structures, hydrographs
- Charts showing time series, cross-sections, rating curves

**Use for:** Reports, presentations, data analysis, documentation

## Troubleshooting

### Common Issues and Solutions

#### "No FLO-2D files found"
**Problem:** The postprocessor can't find valid FLO-2D files  
**Solutions:**
- Verify your folder contains .DAT and .OUT files
- Check file names match FLO-2D conventions (TOPO.DAT, DEPTH.OUT, etc.)
- Ensure files aren't empty or corrupted

#### "Coordinate system error"
**Problem:** Invalid or missing EPSG code  
**Solutions:**
- Double-check your EPSG code
- Try common codes: 2224, 4326, 3857
- Consult your project documentation or GIS specialist

#### "Memory error" or "Process killed"
**Problem:** Not enough RAM for large models  
**Solutions:**
- Close other applications to free memory
- Process smaller sections of your model
- Use a computer with more RAM

#### "Permission denied" errors  
**Problem:** Can't write to output folders  
**Solutions:**
- Run as administrator
- Check folder permissions
- Ensure no files are open in other programs

#### GUI freezes or becomes unresponsive
**Problem:** Long processing time on large models  
**Solutions:**
- Wait patiently - processing can take 10+ minutes
- Use command line for better progress feedback
- Break large models into smaller sections

### Getting Additional Help

1. **Check the logs:** Look for detailed error messages in the output window
2. **Verify your data:** Ensure FLO-2D files are complete and valid
3. **Test with smaller data:** Try processing a subset of your model first
4. **Check system resources:** Monitor RAM and disk space usage

## Advanced Features

### Batch Processing
Process multiple projects automatically:
```bash
python main.py "Project1" "Project2" "Project3" --epsg 2224 --output_format geopackage
```

### Custom Styling
Apply QGIS styles automatically:
1. Create .qml style files with names matching output files
2. Place in a folder (e.g., "C:\Styles")
3. Specify folder path in GUI or `--style_folder` command

### Configuration Files
Save settings in `config.json`:
```json
{
    "flo2d_folders": ["C:/MyProject"],
    "epsg_number": "2224", 
    "output_format": "GeoPackage"
}
```

### Integration with GIS Software

**QGIS (Recommended):**
1. Add raster layers from `flo2d_rasters/`
2. Add vector layers from `flo2d_shp/`
3. Style layers using the built-in symbology tools
4. Create maps, layouts, and presentations

**ArcGIS:**
1. Add data using "Add Data" tool
2. Set symbology for visualization
3. Use geoprocessing tools for analysis
4. Create map layouts and reports

### Performance Optimization

**For large models:**
- Use GeoPackage format instead of Shapefile
- Increase system RAM if possible
- Close unnecessary applications during processing
- Consider processing in sections if memory limited

**For batch processing:**
- Use command line interface
- Process during off-peak hours
- Monitor system resources
- Use solid-state drives (SSD) for better I/O performance

---

*This manual covers the essential features of the FLO-2D Postprocessor. For technical documentation and development information, see the other files in the `docs/` directory.*
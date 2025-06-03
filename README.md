# FLO2D Post-Processor Lite

A Python-based GUI application for post-processing FLO-2D hydraulic model results. This tool provides an intuitive interface for processing FLO-2D output files and converting them to geospatial formats like Shapefiles and GeoPackages.

## Features

- **GUI Interface**: User-friendly graphical interface built with tkinter
- **Batch Processing**: Process multiple FLO-2D project folders simultaneously
- **Multiple Output Formats**: Export data as Shapefiles or GeoPackages
- **Spatial Reference Support**: Configure EPSG codes for proper spatial referencing
- **Style Files Integration**: Apply custom styling to output data
- **Progress Tracking**: Real-time progress monitoring with detailed logging
- **Settings Persistence**: Automatically saves and loads user preferences

## Requirements

- Python 3.7+
- Required Python packages:
  - tkinter (usually included with Python)
  - ttkthemes
  - Additional dependencies as specified in your main processing module

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/postprocessor_for_flo2d.git
   cd postprocessor_for_flo2d
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### GUI Application

Run the GUI application:
```bash
python flo2d_postprocessor_gui.py
```

### Features Overview

1. **Add FLO-2D Folders**: Select one or more FLO-2D project directories to process
2. **EPSG Configuration**: Set the spatial reference system using EPSG codes
3. **Output Format Selection**: Choose between Shapefile or GeoPackage formats
4. **Style Files**: Optionally specify a folder containing style files
5. **Batch Processing**: Process all selected folders with a single click

### Command Line Interface

You can also use the core processing functions directly:
```python
from main import process_flo2d, batch_process_flo2d

# Process a single FLO-2D folder
result = process_flo2d(
    folder_path="path/to/flo2d/project",
    epsg_code=4326,
    create_shapefile=True,
    output_format="Shapefile"
)
```

## Configuration

The application automatically saves your settings in `config.json`, including:
- Previously selected FLO-2D folders
- EPSG number preferences
- Output format selection
- Style files folder location

## File Structure

```
postprocessor_for_flo2d/
├── flo2d_postprocessor_gui.py  # Main GUI application
├── main.py                     # Core processing functions
├── modules/                    # Additional processing modules
├── config.json                 # User settings (auto-generated)
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or feature requests, please open an issue on GitHub.

## Changelog

### Version 1.0.0
- Initial release with GUI interface
- Support for Shapefile and GeoPackage output formats
- Batch processing capabilities
- Settings persistence
- Style files integration 
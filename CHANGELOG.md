# Changelog

All notable changes to the FLO-2D Postprocessor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Breaking: Rename internal 0-based identifier column from `grid_id` to `id` across the codebase. User-facing outputs now expose 1-based `grid_id` (was previously `flo2d_grid_id`).
- Normalize remaining extractors at source (OUTNQ, OUTFLOW, RAIN, EVACUATEDFP) so they emit 0-based `id` without adapters.
- Remove normalization/rename adapters from the orchestrator; merge directly on internal `id`.

### Fixed
- Align OUTNQ time series column headers to 0-based `id` to prevent coordinate merge gaps.

### Docs
- Update STYLE_GUIDE to document `id` (0-based internal) vs `grid_id` (1-based display) conventions with examples.

## [1.0.0] - 2025-01-15

### Added
- Initial public release of FLO-2D Postprocessor
- Comprehensive data extraction from FLO-2D .DAT and .OUT files
- GUI application for easy use by non-programmers
- Command-line interface for advanced users and batch processing
- Support for multiple output formats (Shapefile, GeoPackage, GeoTIFF, Excel, PDF)
- Automated generation of geospatial datasets from FLO-2D results
- Raster creation for flood depth, velocity, and other hydraulic parameters
- Vector data creation for computational domains, channel networks, and hydraulic structures
- Excel report generation with embedded charts and visualizations
- PDF plot generation for cross-sections, rating curves, and hydrographs
- Parallel processing for improved performance with large datasets
- Comprehensive test suite with unit and integration tests
- Support for multiple coordinate systems via EPSG codes
- Style file application for QGIS integration
- Batch processing capabilities for multiple projects
- Error handling and logging throughout the application

### Features
- **Data Extraction**: Supports all major FLO-2D file types including TOPO, DEPTH, VELOC, CHAN, HYSTRUC, SWMM, and many more
- **Geospatial Processing**: Creates properly georeferenced outputs with coordinate system support
- **Visualization**: Generates professional charts, plots, and maps from FLO-2D results
- **User Interface**: Modern GUI with progress tracking and detailed feedback
- **Performance**: Multi-threaded processing and optimized algorithms for large datasets
- **Flexibility**: Configurable output formats and processing options
- **Documentation**: Comprehensive user guide and developer documentation

### Technical Details
- Built with Python 3.8+ compatibility
- Uses GeoPandas, Rasterio, and other leading geospatial libraries
- GUI built with tkinter for cross-platform compatibility
- Extensive test coverage with pytest framework
- Modular architecture for easy maintenance and extension
- Standardized column naming system throughout the codebase
- Robust error handling and user-friendly error messages

### Supported File Types

#### Input Files (.DAT)
- TOPO.DAT - Grid elevation data
- MANNINGS_N.DAT - Surface roughness coefficients
- RAIN.DAT - Rainfall data and time series
- INFIL.DAT - Infiltration parameters (Green-Ampt, SCS, Horton)
- INFLOW.DAT - Inflow boundary conditions
- OUTFLOW.DAT - Outflow boundary locations
- HYSTRUC.DAT - Hydraulic structure definitions
- CHAN.DAT - Channel geometry and properties
- SWMM.inp - SWMM inlet/outlet data
- FPXSEC.DAT - Floodplain cross-section data
- And more...

#### Output Files (.OUT)
- DEPTH.OUT - Maximum water depths
- VELOC.OUT - Velocity magnitude and direction
- MAXWSELEV.OUT - Maximum water surface elevations
- SUPER.OUT - Supercritical flow analysis
- TIME.OUT - Time-related hydraulic parameters
- CHANMAX.OUT - Channel maximum flow values
- HYCROSS.OUT - Cross-section hydraulic data
- HYDROSTRUCT.OUT - Hydraulic structure performance
- And more...

---

## Future Releases

### Planned Features (Future Versions)
- Additional output format support (KML, JSON)
- Enhanced visualization options
- Performance optimizations for very large models
- Additional hydraulic analysis tools
- Plugin system for custom processors
- Cloud processing capabilities
- Integration with other hydraulic modeling software

### Version History Notes
- This is the first public release
- Previous development versions were internal only
- Release numbering follows semantic versioning (MAJOR.MINOR.PATCH)
- Breaking changes will increment MAJOR version
- New features increment MINOR version
- Bug fixes increment PATCH version

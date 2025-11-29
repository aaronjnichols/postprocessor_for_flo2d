"""Output processing modules for FLO-2D Postprocessor.

This package contains modules for creating consolidated outputs:
- geopackage_writer: Writes all vector layers to a single GeoPackage
- qgis_project: Generates QGIS project files (.qgz)
"""

from .geopackage_writer import ConsolidatedGeoPackageWriter
from .qgis_project import QGISProjectGenerator

__all__ = ['ConsolidatedGeoPackageWriter', 'QGISProjectGenerator']

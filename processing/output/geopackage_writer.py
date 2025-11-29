"""Consolidated GeoPackage writer module.

This module provides functionality to write all vector layers to a single
GeoPackage file with multiple layers/tables.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon


# Layer configuration: (layer_name, geometry_type, display_name)
LAYER_CONFIG = {
    # Point layers
    'flow_direction': ('flow_direction', 'Point', 'Flow Direction Points'),
    'super_out_points': ('super_out_points', 'Point', 'Supercritical Flow Points'),
    'evacuatedfp_out_points': ('evacuatedfp_out_points', 'Point', 'Evacuated Floodplain Points'),
    'time_out_points': ('time_out_points', 'Point', 'Time Decrement Points'),
    'inflow_nodes': ('inflow_nodes', 'Point', 'Inflow Nodes'),
    'outflow_nodes': ('outflow_nodes', 'Point', 'Outflow Nodes'),
    'swmm_junctions': ('swmm_junctions', 'Point', 'SWMM Junctions'),
    'swmm_outfalls': ('swmm_outfalls', 'Point', 'SWMM Outfalls'),

    # Line layers
    'fpxsec': ('fpxsec', 'LineString', 'Floodplain Cross Sections'),
    'hydraulic_structures': ('hydraulic_structures', 'LineString', 'Hydraulic Structures'),
    'channel_xsec_lines': ('channel_xsec_lines', 'LineString', 'Channel Cross Section Lines'),
    'channel_bank_segments': ('channel_bank_segments', 'LineString', 'Channel Bank Segments'),
    'swmm_conduits': ('swmm_conduits', 'LineString', 'SWMM Conduits'),

    # Polygon layers
    'computational_domain': ('computational_domain', 'Polygon', 'Computational Domain'),
}


class ConsolidatedGeoPackageWriter:
    """Writer for consolidated GeoPackage with all vector layers.

    This class collects GeoDataFrames and writes them all to a single
    GeoPackage file with each dataset as a separate layer.

    Usage:
        writer = ConsolidatedGeoPackageWriter(output_path, coord_system)
        writer.add_layer('inflow_nodes', gdf)
        writer.add_layer('outflow_nodes', gdf)
        writer.write()  # Writes all layers to the GeoPackage
    """

    def __init__(self, output_dir: str, coord_system: int, filename: str = 'flo2d_results.gpkg'):
        """Initialize the GeoPackage writer.

        Args:
            output_dir: Directory to write the GeoPackage file.
            coord_system: EPSG code for the coordinate reference system.
            filename: Name of the output GeoPackage file.
        """
        self.output_dir = output_dir
        self.coord_system = coord_system
        self.filename = filename
        self.output_path = os.path.join(output_dir, filename)
        self.layers: Dict[str, gpd.GeoDataFrame] = {}
        self.logger = logging.getLogger('FLO2D_Postprocessor')

    def add_layer(self, layer_name: str, gdf: gpd.GeoDataFrame) -> None:
        """Add a layer to be written to the GeoPackage.

        Args:
            layer_name: Name for the layer in the GeoPackage.
            gdf: GeoDataFrame to add as a layer.
        """
        if gdf is None or gdf.empty:
            self.logger.debug(f"Skipping empty layer: {layer_name}")
            return

        # Ensure CRS is set
        if gdf.crs is None:
            gdf = gdf.set_crs(f"EPSG:{self.coord_system}")

        self.layers[layer_name] = gdf
        self.logger.debug(f"Added layer '{layer_name}' with {len(gdf)} features")

    def add_layer_from_file(self, layer_name: str, file_path: str) -> None:
        """Add a layer from an existing file.

        Args:
            layer_name: Name for the layer in the GeoPackage.
            file_path: Path to the source file (shapefile or GeoPackage).
        """
        if not os.path.exists(file_path):
            self.logger.warning(f"File not found, skipping layer: {file_path}")
            return

        try:
            gdf = gpd.read_file(file_path)
            self.add_layer(layer_name, gdf)
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")

    def write(self) -> Optional[str]:
        """Write all layers to the GeoPackage file.

        Returns:
            Path to the created GeoPackage, or None if no layers were written.
        """
        if not self.layers:
            self.logger.warning("No layers to write to GeoPackage")
            return None

        # Remove existing file to start fresh
        if os.path.exists(self.output_path):
            os.remove(self.output_path)

        # Write layers in order: polygons first, then lines, then points
        # This ensures proper layering in GIS applications
        layer_order = self._get_ordered_layers()

        for i, (layer_name, gdf) in enumerate(layer_order):
            try:
                mode = 'w' if i == 0 else 'a'
                gdf.to_file(
                    self.output_path,
                    layer=layer_name,
                    driver='GPKG',
                    mode=mode
                )
                self.logger.info(f"Written layer '{layer_name}' to GeoPackage ({len(gdf)} features)")
            except Exception as e:
                self.logger.error(f"Error writing layer '{layer_name}': {e}")

        self.logger.info(f"Consolidated GeoPackage created: {self.output_path}")
        return self.output_path

    def _get_ordered_layers(self) -> List[Tuple[str, gpd.GeoDataFrame]]:
        """Get layers ordered by geometry type (polygons, lines, points).

        Returns:
            List of (layer_name, gdf) tuples in drawing order.
        """
        polygons = []
        lines = []
        points = []
        other = []

        for layer_name, gdf in self.layers.items():
            if gdf.empty:
                continue

            # Determine geometry type from first non-null geometry
            geom_type = None
            for geom in gdf.geometry:
                if geom is not None:
                    geom_type = geom.geom_type
                    break

            if geom_type in ('Polygon', 'MultiPolygon'):
                polygons.append((layer_name, gdf))
            elif geom_type in ('LineString', 'MultiLineString'):
                lines.append((layer_name, gdf))
            elif geom_type in ('Point', 'MultiPoint'):
                points.append((layer_name, gdf))
            else:
                other.append((layer_name, gdf))

        # Return in order: polygons (bottom), lines, points (top)
        return polygons + lines + points + other

    def get_layer_names(self) -> List[str]:
        """Get list of layer names added to this writer.

        Returns:
            List of layer names.
        """
        return list(self.layers.keys())

    def get_layer(self, layer_name: str) -> Optional[gpd.GeoDataFrame]:
        """Get a specific layer by name.

        Args:
            layer_name: Name of the layer.

        Returns:
            GeoDataFrame for the layer, or None if not found.
        """
        return self.layers.get(layer_name)

    def clear(self) -> None:
        """Clear all layers."""
        self.layers.clear()


def collect_existing_outputs(output_dir: str, coord_system: int) -> ConsolidatedGeoPackageWriter:
    """Collect existing output files into a consolidated GeoPackage writer.

    This function scans the output directory for existing shapefiles and
    GeoPackages and adds them to a new consolidated writer.

    Args:
        output_dir: Directory containing output files (flo2d_shp folder).
        coord_system: EPSG code for coordinate system.

    Returns:
        ConsolidatedGeoPackageWriter with all found layers.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    writer = ConsolidatedGeoPackageWriter(output_dir, coord_system)

    if not os.path.isdir(output_dir):
        logger.warning(f"Output directory not found: {output_dir}")
        return writer

    # Scan for shapefiles and GeoPackages
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)

        if filename.endswith('.shp'):
            layer_name = os.path.splitext(filename)[0]
            writer.add_layer_from_file(layer_name, filepath)

        elif filename.endswith('.gpkg') and filename != 'flo2d_results.gpkg':
            # Read all layers from existing GeoPackage
            try:
                import fiona
                layers = fiona.listlayers(filepath)
                for layer in layers:
                    gdf = gpd.read_file(filepath, layer=layer)
                    writer.add_layer(layer, gdf)
            except Exception as e:
                logger.warning(f"Error reading GeoPackage {filepath}: {e}")
                # Try reading without specifying layer
                try:
                    layer_name = os.path.splitext(filename)[0]
                    gdf = gpd.read_file(filepath)
                    writer.add_layer(layer_name, gdf)
                except Exception:
                    pass

    return writer


def merge_to_consolidated_geopackage(
    source_dir: str,
    output_dir: str,
    coord_system: int,
    filename: str = 'flo2d_results.gpkg'
) -> Optional[str]:
    """Merge all vector outputs into a single consolidated GeoPackage.

    This is a convenience function to merge existing outputs after processing.

    Args:
        source_dir: Directory containing source vector files.
        output_dir: Directory to write the consolidated GeoPackage.
        coord_system: EPSG code for coordinate system.
        filename: Name of the output file.

    Returns:
        Path to the created GeoPackage, or None if failed.
    """
    writer = collect_existing_outputs(source_dir, coord_system)
    writer.output_dir = output_dir
    writer.filename = filename
    writer.output_path = os.path.join(output_dir, filename)
    return writer.write()

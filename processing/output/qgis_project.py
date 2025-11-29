"""QGIS Project file generator module.

This module generates QGIS project files (.qgz) with all FLO-2D output layers
properly styled and organized into groups.
"""

import logging
import os
import uuid
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from xml.dom import minidom

import geopandas as gpd


# Default color ramps for different data types
COLOR_RAMPS = {
    'depth': [
        (0.0, '#FFFFFF'),      # White - no depth
        (0.5, '#D4E6F1'),      # Light blue
        (1.0, '#85C1E9'),      # Medium blue
        (2.0, '#3498DB'),      # Blue
        (5.0, '#2874A6'),      # Dark blue
        (10.0, '#1B4F72'),     # Very dark blue
    ],
    'velocity': [
        (0.0, '#FFFFFF'),      # White
        (1.0, '#ABEBC6'),      # Light green
        (3.0, '#58D68D'),      # Green
        (5.0, '#F7DC6F'),      # Yellow
        (8.0, '#E67E22'),      # Orange
        (12.0, '#E74C3C'),     # Red
    ],
    'elevation': [
        (0.0, '#2E7D32'),      # Dark green (low)
        (0.25, '#81C784'),     # Light green
        (0.5, '#FFF59D'),      # Yellow
        (0.75, '#E57373'),     # Light red
        (1.0, '#5D4037'),      # Brown (high)
    ],
    'time': [
        (0.0, '#FFFFFF'),      # White
        (0.25, '#B3E5FC'),     # Light cyan
        (0.5, '#4FC3F7'),      # Cyan
        (0.75, '#0288D1'),     # Dark cyan
        (1.0, '#01579B'),      # Very dark cyan
    ],
    'discharge': [
        (0.0, '#FFFFFF'),      # White
        (0.2, '#E8F5E9'),      # Very light green
        (0.4, '#81C784'),      # Light green
        (0.6, '#4CAF50'),      # Green
        (0.8, '#2E7D32'),      # Dark green
        (1.0, '#1B5E20'),      # Very dark green
    ],
}

# Layer styling configuration
LAYER_STYLES = {
    # Raster layers
    'depth_max': {'type': 'raster', 'ramp': 'depth', 'label': 'Maximum Depth (ft)'},
    'velocity_max': {'type': 'raster', 'ramp': 'velocity', 'label': 'Maximum Velocity (ft/s)'},
    'velocity_channel': {'type': 'raster', 'ramp': 'velocity', 'label': 'Channel Velocity (ft/s)'},
    'wse_max': {'type': 'raster', 'ramp': 'elevation', 'label': 'Max Water Surface Elevation (ft)'},
    'elev': {'type': 'raster', 'ramp': 'elevation', 'label': 'Ground Elevation (ft)'},
    'time_to_peak': {'type': 'raster', 'ramp': 'time', 'label': 'Time to Peak (hrs)'},
    'time_oneft': {'type': 'raster', 'ramp': 'time', 'label': 'Time to 1ft Depth (hrs)'},
    'time_twoft': {'type': 'raster', 'ramp': 'time', 'label': 'Time to 2ft Depth (hrs)'},
    'q_max': {'type': 'raster', 'ramp': 'discharge', 'label': 'Maximum Discharge (cfs)'},
    'mannings_n': {'type': 'raster', 'ramp': 'elevation', 'label': "Manning's n"},
    'final_depth': {'type': 'raster', 'ramp': 'depth', 'label': 'Final Depth (ft)'},
    'final_velocity': {'type': 'raster', 'ramp': 'velocity', 'label': 'Final Velocity (ft/s)'},
    'infil_depth': {'type': 'raster', 'ramp': 'depth', 'label': 'Infiltration Depth (in)'},
    'rain_depth': {'type': 'raster', 'ramp': 'depth', 'label': 'Rainfall Depth (in)'},
    'arf': {'type': 'raster', 'ramp': 'elevation', 'label': 'Area Reduction Factor'},

    # Vector layers - Points
    'inflow_nodes': {'type': 'point', 'color': '#2ECC71', 'size': 8, 'label': 'Inflow Nodes'},
    'outflow_nodes': {'type': 'point', 'color': '#E74C3C', 'size': 8, 'label': 'Outflow Nodes'},
    'swmm_junctions': {'type': 'point', 'color': '#9B59B6', 'size': 6, 'label': 'SWMM Junctions'},
    'swmm_outfalls': {'type': 'point', 'color': '#E67E22', 'size': 6, 'label': 'SWMM Outfalls'},
    'flow_direction': {'type': 'point', 'color': '#3498DB', 'size': 4, 'label': 'Flow Direction'},
    'super_out_points': {'type': 'point', 'color': '#F39C12', 'size': 5, 'label': 'Supercritical Flow'},
    'evacuatedfp_out_points': {'type': 'point', 'color': '#1ABC9C', 'size': 5, 'label': 'Evacuated Floodplain'},
    'time_out_points': {'type': 'point', 'color': '#34495E', 'size': 5, 'label': 'Time Decrements'},

    # Vector layers - Lines
    'fpxsec': {'type': 'line', 'color': '#8E44AD', 'width': 2, 'label': 'Floodplain Cross Sections'},
    'hydraulic_structures': {'type': 'line', 'color': '#C0392B', 'width': 3, 'label': 'Hydraulic Structures'},
    'channel_xsec_lines': {'type': 'line', 'color': '#2980B9', 'width': 2, 'label': 'Channel Cross Sections'},
    'channel_bank_segments': {'type': 'line', 'color': '#27AE60', 'width': 2, 'label': 'Channel Banks'},
    'swmm_conduits': {'type': 'line', 'color': '#7F8C8D', 'width': 2, 'label': 'SWMM Conduits'},

    # Vector layers - Polygons
    'computational_domain': {'type': 'polygon', 'color': '#3498DB', 'fill_color': '#AED6F1',
                             'opacity': 0.3, 'label': 'Computational Domain'},
}


class QGISProjectGenerator:
    """Generator for QGIS project files (.qgs/.qgz).

    This class creates QGIS project files with all FLO-2D output layers
    properly configured with symbology and organized into layer groups.

    Usage:
        generator = QGISProjectGenerator(project_path, coord_system)
        generator.add_geopackage('/path/to/flo2d_results.gpkg')
        generator.add_raster_folder('/path/to/flo2d_rasters')
        generator.generate()  # Creates the .qgz file
    """

    def __init__(
        self,
        output_dir: str,
        coord_system: int,
        project_name: str = 'flo2d_project'
    ):
        """Initialize the QGIS project generator.

        Args:
            output_dir: Directory to save the project file.
            coord_system: EPSG code for the coordinate reference system.
            project_name: Base name for the project file.
        """
        self.output_dir = output_dir
        self.coord_system = coord_system
        self.project_name = project_name
        self.qgs_path = os.path.join(output_dir, f'{project_name}.qgs')
        self.qgz_path = os.path.join(output_dir, f'{project_name}.qgz')
        self.logger = logging.getLogger('FLO2D_Postprocessor')

        self.raster_layers: List[Tuple[str, str]] = []  # (name, path)
        self.vector_layers: List[Tuple[str, str, str]] = []  # (name, path, layer_name)
        self.geopackage_path: Optional[str] = None

    def add_raster(self, name: str, raster_path: str) -> None:
        """Add a raster layer to the project.

        Args:
            name: Layer name.
            raster_path: Path to the raster file.
        """
        if os.path.exists(raster_path):
            self.raster_layers.append((name, raster_path))
            self.logger.debug(f"Added raster layer: {name}")

    def add_raster_folder(self, folder_path: str) -> None:
        """Add all rasters from a folder.

        Args:
            folder_path: Path to folder containing raster files.
        """
        if not os.path.isdir(folder_path):
            self.logger.warning(f"Raster folder not found: {folder_path}")
            return

        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.tif', '.tiff')):
                name = os.path.splitext(filename)[0]
                path = os.path.join(folder_path, filename)
                self.add_raster(name, path)

    def add_vector(self, name: str, file_path: str, layer_name: Optional[str] = None) -> None:
        """Add a vector layer to the project.

        Args:
            name: Layer name for display.
            file_path: Path to the vector file.
            layer_name: Layer name within file (for GeoPackages).
        """
        if os.path.exists(file_path):
            self.vector_layers.append((name, file_path, layer_name or name))
            self.logger.debug(f"Added vector layer: {name}")

    def add_geopackage(self, gpkg_path: str) -> None:
        """Add all layers from a GeoPackage.

        Args:
            gpkg_path: Path to the GeoPackage file.
        """
        if not os.path.exists(gpkg_path):
            self.logger.warning(f"GeoPackage not found: {gpkg_path}")
            return

        self.geopackage_path = gpkg_path

        try:
            import fiona
            layers = fiona.listlayers(gpkg_path)
            for layer in layers:
                self.add_vector(layer, gpkg_path, layer)
        except ImportError:
            # Fallback without fiona
            try:
                gdf = gpd.read_file(gpkg_path)
                # Single layer fallback
                name = os.path.splitext(os.path.basename(gpkg_path))[0]
                self.add_vector(name, gpkg_path, None)
            except Exception as e:
                self.logger.error(f"Error reading GeoPackage: {e}")

    def add_vector_folder(self, folder_path: str) -> None:
        """Add all vector files from a folder.

        Args:
            folder_path: Path to folder containing vector files.
        """
        if not os.path.isdir(folder_path):
            self.logger.warning(f"Vector folder not found: {folder_path}")
            return

        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)

            if filename.lower().endswith('.shp'):
                name = os.path.splitext(filename)[0]
                self.add_vector(name, filepath)

            elif filename.lower().endswith('.gpkg'):
                self.add_geopackage(filepath)

    def generate(self) -> Optional[str]:
        """Generate the QGIS project file.

        Returns:
            Path to the created .qgz file, or None if failed.
        """
        try:
            # Create the QGS XML structure
            root = self._create_project_xml()

            # Write to QGS file
            xml_str = ET.tostring(root, encoding='unicode')
            # Pretty print
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent='  ')
            # Remove extra blank lines
            pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])

            with open(self.qgs_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

            # Create QGZ (zipped QGS)
            with zipfile.ZipFile(self.qgz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(self.qgs_path, os.path.basename(self.qgs_path))

            # Remove the uncompressed QGS file
            os.remove(self.qgs_path)

            self.logger.info(f"QGIS project created: {self.qgz_path}")
            return self.qgz_path

        except Exception as e:
            self.logger.error(f"Error generating QGIS project: {e}")
            return None

    def _create_project_xml(self) -> ET.Element:
        """Create the QGIS project XML structure.

        Returns:
            Root Element of the project XML.
        """
        # Create root element
        qgis = ET.Element('qgis', {
            'projectname': self.project_name,
            'version': '3.28.0-Firenze',
            'saveDateTime': datetime.now().isoformat(),
            'saveUser': 'FLO2D_Postprocessor',
        })

        # Add project CRS
        self._add_project_crs(qgis)

        # Add layer tree (groups and layers)
        layer_tree = ET.SubElement(qgis, 'layer-tree-group')
        layer_tree.set('name', '')
        layer_tree.set('expanded', '1')
        layer_tree.set('checked', 'Qt::Checked')

        # Create groups
        raster_group = self._add_layer_group(layer_tree, 'Rasters', True)
        vector_group = self._add_layer_group(layer_tree, 'Vectors', True)
        points_group = self._add_layer_group(vector_group, 'Points', True)
        lines_group = self._add_layer_group(vector_group, 'Lines', True)
        polygons_group = self._add_layer_group(vector_group, 'Polygons', True)

        # Track all layer IDs
        layer_ids = []

        # Add map layers container
        project_layers = ET.SubElement(qgis, 'projectlayers')

        # Add raster layers
        for name, path in self.raster_layers:
            layer_id = self._generate_layer_id(name)
            layer_ids.append(layer_id)

            # Add to tree
            self._add_layer_tree_item(raster_group, name, layer_id, 'raster')

            # Add layer definition
            self._add_raster_layer(project_layers, name, path, layer_id)

        # Add vector layers
        for name, path, layer_name in self.vector_layers:
            layer_id = self._generate_layer_id(name)
            layer_ids.append(layer_id)

            # Determine geometry type and group
            style = LAYER_STYLES.get(name, {})
            layer_type = style.get('type', 'point')

            if layer_type == 'polygon':
                group = polygons_group
            elif layer_type == 'line':
                group = lines_group
            else:
                group = points_group

            # Add to tree
            self._add_layer_tree_item(group, name, layer_id, 'vector')

            # Add layer definition
            self._add_vector_layer(project_layers, name, path, layer_name, layer_id)

        # Add layer order
        self._add_layer_order(qgis, layer_ids)

        return qgis

    def _add_project_crs(self, root: ET.Element) -> None:
        """Add project CRS definition."""
        proj_crs = ET.SubElement(root, 'projectCrs')
        spatial_ref = ET.SubElement(proj_crs, 'spatialrefsys')
        ET.SubElement(spatial_ref, 'authid').text = f'EPSG:{self.coord_system}'

    def _add_layer_group(
        self,
        parent: ET.Element,
        name: str,
        expanded: bool = True
    ) -> ET.Element:
        """Add a layer group to the tree."""
        group = ET.SubElement(parent, 'layer-tree-group', {
            'name': name,
            'expanded': '1' if expanded else '0',
            'checked': 'Qt::Checked',
        })
        return group

    def _add_layer_tree_item(
        self,
        parent: ET.Element,
        name: str,
        layer_id: str,
        layer_type: str
    ) -> None:
        """Add a layer item to the tree."""
        ET.SubElement(parent, 'layer-tree-layer', {
            'name': name,
            'id': layer_id,
            'source': '',
            'providerKey': 'gdal' if layer_type == 'raster' else 'ogr',
            'expanded': '0',
            'checked': 'Qt::Checked',
        })

    def _add_raster_layer(
        self,
        parent: ET.Element,
        name: str,
        path: str,
        layer_id: str
    ) -> None:
        """Add a raster layer definition."""
        # Make path relative if in same directory
        rel_path = self._get_relative_path(path)

        layer = ET.SubElement(parent, 'maplayer', {
            'type': 'raster',
            'hasScaleBasedVisibilityFlag': '0',
            'autoRefreshEnabled': '0',
        })

        ET.SubElement(layer, 'id').text = layer_id
        ET.SubElement(layer, 'layername').text = name
        ET.SubElement(layer, 'datasource').text = rel_path
        ET.SubElement(layer, 'provider').text = 'gdal'

        # Add CRS
        srs = ET.SubElement(layer, 'srs')
        spatial_ref = ET.SubElement(srs, 'spatialrefsys')
        ET.SubElement(spatial_ref, 'authid').text = f'EPSG:{self.coord_system}'

        # Add basic renderer
        self._add_raster_renderer(layer, name)

    def _add_vector_layer(
        self,
        parent: ET.Element,
        name: str,
        path: str,
        layer_name: str,
        layer_id: str
    ) -> None:
        """Add a vector layer definition."""
        # Determine data source string
        rel_path = self._get_relative_path(path)

        if path.lower().endswith('.gpkg'):
            datasource = f"{rel_path}|layername={layer_name}"
        else:
            datasource = rel_path

        layer = ET.SubElement(parent, 'maplayer', {
            'type': 'vector',
            'geometry': self._get_geometry_type(name),
            'hasScaleBasedVisibilityFlag': '0',
            'autoRefreshEnabled': '0',
        })

        ET.SubElement(layer, 'id').text = layer_id
        ET.SubElement(layer, 'layername').text = name
        ET.SubElement(layer, 'datasource').text = datasource
        ET.SubElement(layer, 'provider').text = 'ogr'

        # Add CRS
        srs = ET.SubElement(layer, 'srs')
        spatial_ref = ET.SubElement(srs, 'spatialrefsys')
        ET.SubElement(spatial_ref, 'authid').text = f'EPSG:{self.coord_system}'

        # Add renderer with styling
        self._add_vector_renderer(layer, name)

    def _add_raster_renderer(self, layer: ET.Element, name: str) -> None:
        """Add raster renderer with color ramp."""
        style = LAYER_STYLES.get(name, {})
        ramp_name = style.get('ramp', 'depth')
        color_ramp = COLOR_RAMPS.get(ramp_name, COLOR_RAMPS['depth'])

        pipe = ET.SubElement(layer, 'pipe')
        renderer = ET.SubElement(pipe, 'rasterrenderer', {
            'type': 'singlebandpseudocolor',
            'band': '1',
            'opacity': '1',
        })

        # Add color ramp
        shader = ET.SubElement(renderer, 'rastershader')
        func = ET.SubElement(shader, 'colorrampshader', {
            'colorRampType': 'INTERPOLATED',
            'classificationMode': '1',
        })

        for value, color in color_ramp:
            ET.SubElement(func, 'item', {
                'value': str(value),
                'color': color,
                'label': str(value),
            })

    def _add_vector_renderer(self, layer: ET.Element, name: str) -> None:
        """Add vector renderer with appropriate symbology."""
        style = LAYER_STYLES.get(name, {})
        layer_type = style.get('type', 'point')

        renderer = ET.SubElement(layer, 'renderer-v2', {'type': 'singleSymbol'})
        symbols = ET.SubElement(renderer, 'symbols')
        symbol = ET.SubElement(symbols, 'symbol', {
            'name': '0',
            'type': 'marker' if layer_type == 'point' else ('line' if layer_type == 'line' else 'fill'),
            'alpha': str(style.get('opacity', 1.0)),
        })

        layer_elem = ET.SubElement(symbol, 'layer', {
            'class': self._get_symbol_class(layer_type),
            'enabled': '1',
            'locked': '0',
        })

        # Add symbol properties
        if layer_type == 'point':
            self._add_prop(layer_elem, 'color', style.get('color', '#3498DB'))
            self._add_prop(layer_elem, 'size', str(style.get('size', 4)))
            self._add_prop(layer_elem, 'name', 'circle')
        elif layer_type == 'line':
            self._add_prop(layer_elem, 'line_color', style.get('color', '#3498DB'))
            self._add_prop(layer_elem, 'line_width', str(style.get('width', 1)))
        else:  # polygon
            self._add_prop(layer_elem, 'color', style.get('fill_color', '#AED6F1'))
            self._add_prop(layer_elem, 'outline_color', style.get('color', '#3498DB'))
            self._add_prop(layer_elem, 'outline_width', '0.5')

    def _add_prop(self, parent: ET.Element, key: str, value: str) -> None:
        """Add a property element."""
        ET.SubElement(parent, 'prop', {'k': key, 'v': value})

    def _add_layer_order(self, root: ET.Element, layer_ids: List[str]) -> None:
        """Add layer rendering order."""
        order = ET.SubElement(root, 'layerorder')
        for layer_id in reversed(layer_ids):
            ET.SubElement(order, 'layer', {'id': layer_id})

    def _generate_layer_id(self, name: str) -> str:
        """Generate a unique layer ID."""
        return f"{name}_{uuid.uuid4().hex[:8]}"

    def _get_relative_path(self, path: str) -> str:
        """Get path relative to project directory."""
        try:
            return os.path.relpath(path, self.output_dir)
        except ValueError:
            # Different drives on Windows
            return path

    def _get_geometry_type(self, name: str) -> str:
        """Get QGIS geometry type string."""
        style = LAYER_STYLES.get(name, {})
        layer_type = style.get('type', 'point')
        return {'point': 'Point', 'line': 'Line', 'polygon': 'Polygon'}.get(layer_type, 'Point')

    def _get_symbol_class(self, layer_type: str) -> str:
        """Get QGIS symbol class name."""
        return {
            'point': 'SimpleMarker',
            'line': 'SimpleLine',
            'polygon': 'SimpleFill',
        }.get(layer_type, 'SimpleMarker')


def create_qgis_project(
    project_dir: str,
    coord_system: int,
    geopackage_path: Optional[str] = None,
    raster_folder: Optional[str] = None,
    vector_folder: Optional[str] = None,
    project_name: str = 'flo2d_project'
) -> Optional[str]:
    """Convenience function to create a QGIS project file.

    Args:
        project_dir: Directory to save the project file.
        coord_system: EPSG code for coordinate system.
        geopackage_path: Path to consolidated GeoPackage (optional).
        raster_folder: Path to folder with rasters (optional).
        vector_folder: Path to folder with vectors (optional).
        project_name: Name for the project file.

    Returns:
        Path to the created .qgz file, or None if failed.
    """
    generator = QGISProjectGenerator(project_dir, coord_system, project_name)

    if geopackage_path:
        generator.add_geopackage(geopackage_path)

    if raster_folder:
        generator.add_raster_folder(raster_folder)

    if vector_folder and not geopackage_path:
        generator.add_vector_folder(vector_folder)

    return generator.generate()

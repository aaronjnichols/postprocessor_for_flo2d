"""Computational domain polygon vectorization module.

This module generates the outer perimeter polygon of the FLO-2D computational
model domain using optimized boundary-edge detection algorithms.
"""

# Standard library imports
import logging
import os
import time
from typing import Optional, Tuple, Set

# Third-party imports
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import polygonize
from shapely import unary_union

# Local application imports
from core.constants import (
    X_COORD, Y_COORD, GRID_ID, GEOMETRY,
    DOMAIN_VECTORIZATION_MIN_GRID_SIZE,
    DOMAIN_VECTORIZATION_PRECISION_DECIMALS,
    ALGORITHM_AUTO, ALGORITHM_BOUNDARY_EDGES, ALGORITHM_BOUNDARY_CELLS,
    ALGORITHM_ALL_CELLS, ALGORITHM_BOUNDING_BOX
)
from core.logger import TimingLogger
from core.utilities import time_function

# Module constants (using values from constants.py)
DEFAULT_PRECISION_DECIMALS = DOMAIN_VECTORIZATION_PRECISION_DECIMALS
MIN_GRID_SIZE_FOR_EDGE_ALGORITHM = DOMAIN_VECTORIZATION_MIN_GRID_SIZE


def _detect_header_rows(file_path: str) -> int:
    """
    Detect number of header rows to skip in DEPTH.OUT file.
    
    Args:
        file_path (str): Path to the DEPTH.OUT file.
        
    Returns:
        int: Number of rows to skip.
    """
    def numeric_line(line):
        try:
            [float(i) for i in line.strip().split()]
            return True
        except ValueError:
            return False

    with open(file_path, 'r') as f:
        first = f.readline()
    return 0 if numeric_line(first) else 1


def _calculate_cell_size(x_coords: np.ndarray, y_coords: np.ndarray) -> float:
    """
    Calculate the cell size from coordinate arrays.
    
    Args:
        x_coords (np.ndarray): Array of x coordinates.
        y_coords (np.ndarray): Array of y coordinates.
        
    Returns:
        float: Cell size (minimum spacing between coordinates).
    """
    ux = np.sort(np.unique(x_coords))
    uy = np.sort(np.unique(y_coords))
    dx = np.diff(ux)
    dy = np.diff(uy)
    
    # Get minimum positive spacing
    dx_min = dx[dx > 0].min() if len(dx[dx > 0]) > 0 else 1.0
    dy_min = dy[dy > 0].min() if len(dy[dy > 0]) > 0 else 1.0
    
    return float(min(dx_min, dy_min))


def _round_coordinate(point: Tuple[float, float], decimals: int) -> Tuple[float, float]:
    """
    Round coordinate to specified decimal places.
    
    Args:
        point (Tuple[float, float]): Coordinate point (x, y).
        decimals (int): Number of decimal places.
        
    Returns:
        Tuple[float, float]: Rounded coordinate.
    """
    return (round(point[0], decimals), round(point[1], decimals))


def _create_domain_from_boundary_edges(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    precision_decimals: int = DEFAULT_PRECISION_DECIMALS
) -> MultiPolygon:
    """
    Create domain polygon using boundary edge detection algorithm.
    
    This algorithm identifies the outer boundary by tracking cell edges.
    Edges shared by adjacent cells cancel out, leaving only boundary edges.
    
    Args:
        x_coords (np.ndarray): Array of x coordinates.
        y_coords (np.ndarray): Array of y coordinates.
        precision_decimals (int): Decimal precision for coordinate rounding.
        
    Returns:
        MultiPolygon: Domain boundary polygon(s).
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    timing_logger = TimingLogger(logger)
    
    # Calculate cell size
    cell_size = _calculate_cell_size(x_coords, y_coords)
    half_cell = cell_size / 2.0
    
    timing_logger.log("Cell size calculation completed")
    
    # Create boundary edge set using the efficient algorithm
    boundary_edges = set()
    
    for x, y in zip(x_coords, y_coords):
        # Create cell corner coordinates
        lower_left = (x - half_cell, y - half_cell)
        lower_right = (x + half_cell, y - half_cell)
        upper_right = (x + half_cell, y + half_cell)
        upper_left = (x - half_cell, y + half_cell)
        
        # Define cell edges
        cell_edges = [
            (_round_coordinate(lower_left, precision_decimals), 
             _round_coordinate(lower_right, precision_decimals)),
            (_round_coordinate(lower_right, precision_decimals), 
             _round_coordinate(upper_right, precision_decimals)),
            (_round_coordinate(upper_right, precision_decimals), 
             _round_coordinate(upper_left, precision_decimals)),
            (_round_coordinate(upper_left, precision_decimals), 
             _round_coordinate(lower_left, precision_decimals)),
        ]
        
        # Process each edge (boundary detection logic)
        for edge in cell_edges:
            edge_key = tuple(sorted(edge))
            if edge_key in boundary_edges:
                boundary_edges.remove(edge_key)
            else:
                boundary_edges.add(edge_key)
    
    timing_logger.log(f"Boundary edge detection completed - {len(boundary_edges)} edges found")
    
    # Convert edges to LineStrings and polygonize
    lines = [LineString([edge[0], edge[1]]) for edge in boundary_edges]
    polygons = list(polygonize(lines))
    
    timing_logger.log("Polygonization completed")
    
    return MultiPolygon(polygons)


def _select_algorithm(
    coord_count: int,
    algorithm: str = ALGORITHM_AUTO
) -> str:
    """
    Select the optimal algorithm based on data characteristics.
    
    Args:
        coord_count (int): Number of coordinate points.
        algorithm (str): Algorithm preference (auto, boundary_edges, boundary_cells, all_cells, bounding_box).
        
    Returns:
        str: Selected algorithm name.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if algorithm != ALGORITHM_AUTO:
        return algorithm
    
    # Use boundary edge algorithm for larger grids
    if coord_count >= MIN_GRID_SIZE_FOR_EDGE_ALGORITHM:
        logger.info(f"Large grid ({coord_count} cells) - using boundary edge algorithm")
        return ALGORITHM_BOUNDARY_EDGES
    
    # For smaller grids, use simpler methods
    if coord_count < 50:
        logger.info(f"Very small grid ({coord_count} cells) - using bounding box algorithm")
        return ALGORITHM_BOUNDING_BOX
    else:
        logger.info(f"Small grid ({coord_count} cells) - using boundary cells algorithm")
        return ALGORITHM_BOUNDARY_CELLS


@time_function
def create_domain_polygon_from_depth_file(
    depth_file_path: str,
    coord_system: int,
    output_path: str,
    output_format: str = "Shapefile"
) -> str:
    """
    Create domain polygon directly from DEPTH.OUT file.
    
    This function provides an efficient way to create domain polygons
    by reading coordinates directly from DEPTH.OUT files without
    requiring a pre-processed GeoDataFrame.
    
    Args:
        depth_file_path (str): Path to the DEPTH.OUT file.
        coord_system (int): EPSG code for spatial reference.
        output_path (str): Directory to save the output file.
        output_format (str, optional): "Shapefile" or "GeoPackage". Defaults to "Shapefile".
        
    Returns:
        str: Path to the created shapefile or geopackage.
        
    Raises:
        FileNotFoundError: If DEPTH.OUT file is not found.
        ValueError: If unsupported output format is specified.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if not os.path.exists(depth_file_path):
        raise FileNotFoundError(f"DEPTH.OUT file not found: {depth_file_path}")
    
    # Detect header rows
    skiprows = _detect_header_rows(depth_file_path)
    
    # Read coordinates efficiently
    df = pd.read_csv(
        depth_file_path,
        sep=r'\s+',
        header=None,
        skiprows=skiprows,
        usecols=[1, 2],  # x, y coordinates (0-based indexing)
        names=[X_COORD, Y_COORD],
        dtype=float
    )
    
    logger.info(f"Loaded {len(df)} grid points from DEPTH.OUT")
    
    # Create domain using boundary edge algorithm
    domain_polygon = _create_domain_from_boundary_edges(
        df[X_COORD].values,
        df[Y_COORD].values
    )
    
    # Convert MultiPolygon to single Polygon if needed
    if hasattr(domain_polygon, 'geoms'):
        # If it's a MultiPolygon, get the largest polygon
        perimeter_poly = max(domain_polygon.geoms, key=lambda p: p.area)
    else:
        perimeter_poly = domain_polygon
    
    if perimeter_poly is None or perimeter_poly.is_empty:
        logger.error("Failed to generate perimeter polygon from DEPTH.OUT data")
        return None

    # Create GeoDataFrame
    gdf_perim = gpd.GeoDataFrame(
        {"name": ["computational_domain"]},
        geometry=[perimeter_poly],
        crs=f"EPSG:{coord_system}",
    )

    # Save output file
    if output_format == "Shapefile":
        output_file = os.path.join(output_path, "computational_domain.shp")
        gdf_perim.to_file(output_file, driver="ESRI Shapefile")
    elif output_format == "GeoPackage":
        output_file = os.path.join(output_path, "computational_domain.gpkg")
        gdf_perim.to_file(output_file, layer="grid_perimeter", driver="GPKG")
    else:
        logger.error(
            f"Unsupported output format: {output_format}. Expected 'Shapefile' or 'GeoPackage'."
        )
        raise ValueError(
            f"Unsupported output format: {output_format}. Expected 'Shapefile' or 'GeoPackage'."
        )

    logger.info(f"Computational domain {output_format} created at: {output_file}")
    return output_file


@time_function
def create_domain_polygon(
    model_geo_df: Optional[gpd.GeoDataFrame] = None,
    coord_system: int = None,
    output_path: str = None,
    output_format: str = "Shapefile",
    algorithm: str = ALGORITHM_AUTO,
    depth_file_path: Optional[str] = None
) -> str:
    """
    Create a vector file of the model computational domain perimeter.

    This function supports multiple input methods and algorithms for creating
    domain polygons with backward compatibility and enhanced performance.

    Args:
        model_geo_df (gpd.GeoDataFrame, optional): GeoDataFrame with x and y
            coordinate columns representing cell centres.
        coord_system (int): EPSG code for spatial reference.
        output_path (str): Directory to save the output file.
        output_format (str, optional): "Shapefile" or "GeoPackage". Defaults to "Shapefile".
        algorithm (str, optional): Algorithm to use (auto, boundary_edges, 
            boundary_cells, all_cells, bounding_box). Defaults to auto.
        depth_file_path (str, optional): Path to DEPTH.OUT file for direct processing.

    Returns:
        str: Path to the created shapefile or geopackage.
        
    Raises:
        ValueError: If neither model_geo_df nor depth_file_path is provided,
                   or if unsupported output format is specified.
        KeyError: If model_geo_df is missing required columns.
        FileNotFoundError: If depth_file_path is specified but file doesn't exist.
    """
    logger = logging.getLogger("FLO2D_Postprocessor")

    # Option 1: Direct from DEPTH.OUT file (new, efficient)
    if depth_file_path:
        return create_domain_polygon_from_depth_file(
            depth_file_path, coord_system, output_path, output_format
        )

    # Option 2: From existing GeoDataFrame (backward compatibility)
    if model_geo_df is None or model_geo_df.empty:
        raise ValueError("Either model_geo_df or depth_file_path must be provided")

    if not {X_COORD, Y_COORD}.issubset(model_geo_df.columns):
        missing = {X_COORD, Y_COORD} - set(model_geo_df.columns)
        logger.error(f"Model GeoDataFrame missing required columns: {missing}")
        raise KeyError(f"Model GeoDataFrame missing required columns: {missing}")

    # Extract coordinates
    x_coords = model_geo_df[X_COORD].values
    y_coords = model_geo_df[Y_COORD].values
    coord_count = len(x_coords)
    
    # Select algorithm based on data characteristics
    selected_algorithm = _select_algorithm(coord_count, algorithm)
    
    # Execute selected algorithm
    if selected_algorithm == ALGORITHM_BOUNDARY_EDGES:
        domain_polygon = _create_domain_from_boundary_edges(x_coords, y_coords)
        # Convert MultiPolygon to single Polygon if needed
        if hasattr(domain_polygon, 'geoms'):
            perimeter_poly = max(domain_polygon.geoms, key=lambda p: p.area)
        else:
            perimeter_poly = domain_polygon
            
    elif selected_algorithm == ALGORITHM_BOUNDING_BOX:
        logger.info(f"Very small grid ({coord_count} cells), using bounding box approach")
        cell_size = _calculate_cell_size(x_coords, y_coords)
        half = cell_size / 2.0
        min_x, max_x = x_coords.min(), x_coords.max()
        min_y, max_y = y_coords.min(), y_coords.max()
        perimeter_poly = box(min_x - half, min_y - half, max_x + half, max_y + half)
        
    elif selected_algorithm == ALGORITHM_ALL_CELLS:
        logger.info(f"Small grid ({coord_count} cells), using all-cells method")
        cell_size = _calculate_cell_size(x_coords, y_coords)
        half = cell_size / 2.0
        minx = x_coords - half
        maxx = x_coords + half
        miny = y_coords - half
        maxy = y_coords + half
        
        boxes = [box(minx[i], miny[i], maxx[i], maxy[i]) 
                 for i in range(len(x_coords))]
        perimeter_poly = unary_union(boxes)
        
        # Convert MultiPolygon to single Polygon if needed
        if hasattr(perimeter_poly, 'geoms'):
            perimeter_poly = max(perimeter_poly.geoms, key=lambda p: p.area)
            
    else:  # boundary_cells (fallback method)
        logger.info(f"Medium grid ({coord_count} cells), using boundary cells method")
        cell_size = _calculate_cell_size(x_coords, y_coords)
        half = cell_size / 2.0
        
        # Create a set for faster lookup
        grid_positions = set()
        for x, y in zip(x_coords, y_coords):
            grid_x = round(x / cell_size) * cell_size
            grid_y = round(y / cell_size) * cell_size
            grid_positions.add((grid_x, grid_y))
        
        # Find boundary cells
        boundary_cells = []
        for grid_pos in grid_positions:
            gx, gy = grid_pos
            neighbors = [
                (gx + cell_size, gy),
                (gx - cell_size, gy),
                (gx, gy + cell_size),
                (gx, gy - cell_size)
            ]
            
            if any(neighbor not in grid_positions for neighbor in neighbors):
                boundary_cells.append(grid_pos)
        
        # Create boxes for boundary cells
        boundary_boxes = []
        for bx, by in boundary_cells:
            boundary_boxes.append(box(bx - half, by - half, bx + half, by + half))
        
        perimeter_poly = unary_union(boundary_boxes)
        
        # Fill any interior holes
        if hasattr(perimeter_poly, 'exterior'):
            perimeter_poly = Polygon(perimeter_poly.exterior)
        elif hasattr(perimeter_poly, 'geoms'):
            perimeter_poly = max(perimeter_poly.geoms, key=lambda p: p.area)

    if perimeter_poly is None or perimeter_poly.is_empty:
        logger.error("Failed to generate perimeter polygon from model data")
        return None

    # Create GeoDataFrame
    gdf_perim = gpd.GeoDataFrame(
        {"name": ["computational_domain"]},
        geometry=[perimeter_poly],
        crs=f"EPSG:{coord_system}",
    )

    # Save output file
    if output_format == "Shapefile":
        output_file = os.path.join(output_path, "computational_domain.shp")
        gdf_perim.to_file(output_file, driver="ESRI Shapefile")
    elif output_format == "GeoPackage":
        output_file = os.path.join(output_path, "computational_domain.gpkg")
        gdf_perim.to_file(output_file, layer="grid_perimeter", driver="GPKG")
    else:
        logger.error(
            f"Unsupported output format: {output_format}. Expected 'Shapefile' or 'GeoPackage'."
        )
        raise ValueError(
            f"Unsupported output format: {output_format}. Expected 'Shapefile' or 'GeoPackage'."
        )

    logger.info(f"Computational domain {output_format} created at: {output_file}")
    return output_file
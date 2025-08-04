"""Computational domain polygon vectorization module.

This module generates the outer perimeter polygon of the FLO-2D computational
model domain using the model data GeoDataFrame.
"""

# Standard library imports
import logging
import os

# Third-party imports
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, box, MultiPoint
from shapely import unary_union

# Local application imports
from core.constants import X_COORD, Y_COORD
from core.utilities import time_function


@time_function
def create_domain_polygon(
    model_geo_df: gpd.GeoDataFrame,
    coord_system: int,
    output_path: str,
    output_format: str = "Shapefile",
) -> str:
    """Create a vector file of the model computational domain perimeter.

    Args:
        model_geo_df (gpd.GeoDataFrame): GeoDataFrame with ``x`` and ``y``
            coordinate columns representing cell centres.
        coord_system (int): EPSG code for spatial reference.
        output_path (str): Directory to save the output file.
        output_format (str, optional): ``"Shapefile"`` or ``"GeoPackage"``.
            Defaults to ``"Shapefile"``.

    Returns:
        str: Path to the created shapefile or geopackage.
    """
    logger = logging.getLogger("FLO2D_Postprocessor")

    if model_geo_df is None or model_geo_df.empty:
        logger.warning("Model GeoDataFrame is empty. Skipping domain polygon creation.")
        return None

    if not {X_COORD, Y_COORD}.issubset(model_geo_df.columns):
        missing = {X_COORD, Y_COORD} - set(model_geo_df.columns)
        logger.error(f"Model GeoDataFrame missing required columns: {missing}")
        raise KeyError(f"Model GeoDataFrame missing required columns: {missing}")

    # Extract coordinates
    x_coords = model_geo_df[X_COORD].values
    y_coords = model_geo_df[Y_COORD].values
    
    # Find the typical spacing between cells
    ux = np.unique(x_coords)
    uy = np.unique(y_coords)
    
    if len(ux) < 2 or len(uy) < 2:
        logger.error("Insufficient unique coordinates to determine grid spacing")
        return None
    
    dx = np.diff(ux)
    dy = np.diff(uy)
    cell_size = (np.median(dx) + np.median(dy)) / 2.0
    half = cell_size / 2.0
    
    # OPTIMIZED APPROACH: Use a grid-based method for efficiency
    # Instead of creating and merging thousands of individual boxes,
    # we identify the boundary cells directly
    
    # Create a set for faster lookup (sets are faster than dicts for membership testing)
    grid_positions = set()
    coord_to_grid = {}  # Map original coordinates to grid positions
    
    for x, y in zip(x_coords, y_coords):
        # Round to nearest grid position to handle floating point issues
        grid_x = round(x / cell_size) * cell_size
        grid_y = round(y / cell_size) * cell_size
        grid_pos = (grid_x, grid_y)
        grid_positions.add(grid_pos)
        coord_to_grid[(x, y)] = grid_pos
    
    # Find boundary cells more efficiently
    boundary_cells = []
    for grid_pos in grid_positions:
        gx, gy = grid_pos
        # Check 4 neighbors (N, S, E, W)
        neighbors = [
            (gx + cell_size, gy),
            (gx - cell_size, gy),
            (gx, gy + cell_size),
            (gx, gy - cell_size)
        ]
        
        # If any neighbor is missing, this is a boundary cell
        if any(neighbor not in grid_positions for neighbor in neighbors):
            boundary_cells.append(grid_pos)
    
    # Determine if boundary approach is worth it
    total_cells = len(x_coords)
    boundary_count = len(boundary_cells)
    
    # Use boundary method only if it reduces work significantly
    # For small grids or when boundary ratio is high, use simpler approaches
    boundary_ratio = boundary_count / total_cells if total_cells > 0 else 1.0
    
    if total_cells < 500 or boundary_ratio > 0.6:
        # For small grids or when most cells are boundaries, use simpler method
        if total_cells < 50:
            # Very small grid - use bounding box
            logger.info(f"Very small grid ({total_cells} cells), using bounding box approach")
            min_x, max_x = x_coords.min(), x_coords.max()
            min_y, max_y = y_coords.min(), y_coords.max()
            perimeter_poly = box(min_x - half, min_y - half, max_x + half, max_y + half)
        else:
            # Small/medium grid with high boundary ratio - use all cells method
            logger.info(f"Small grid or high boundary ratio ({boundary_ratio:.2f}), using all-cells method")
            minx = x_coords - half
            maxx = x_coords + half
            miny = y_coords - half
            maxy = y_coords + half
            
            boxes = [box(minx[i], miny[i], maxx[i], maxy[i]) 
                     for i in range(len(x_coords))]
            perimeter_poly = unary_union(boxes)
    else:
        # Create boxes only for boundary cells
        logger.info(f"Creating domain from {len(boundary_cells)} boundary cells (out of {len(x_coords)} total)")
        boundary_boxes = []
        for bx, by in boundary_cells:
            boundary_boxes.append(box(bx - half, by - half, bx + half, by + half))
        
        # Union boundary boxes - much faster with fewer boxes
        perimeter_poly = unary_union(boundary_boxes)
        
        # Fill any interior holes (we want the outer boundary only)
        if hasattr(perimeter_poly, 'exterior'):
            perimeter_poly = Polygon(perimeter_poly.exterior)
    
    # Convert MultiPolygon to single Polygon if needed
    if hasattr(perimeter_poly, 'geoms'):
        # If it's a MultiPolygon, get the largest polygon
        perimeter_poly = max(perimeter_poly.geoms, key=lambda p: p.area)
    
    if perimeter_poly is None or perimeter_poly.is_empty:
        logger.error("Failed to generate perimeter polygon from model data")
        return None

    gdf_perim = gpd.GeoDataFrame(
        {"name": ["computational_domain"]},
        geometry=[perimeter_poly],
        crs=f"EPSG:{coord_system}",
    )

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
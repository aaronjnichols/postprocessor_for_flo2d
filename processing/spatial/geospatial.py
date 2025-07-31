"""Geospatial processing utilities for FLO-2D data.

This module provides functions for converting FLO-2D model data into
geospatial formats and performing spatial calculations.
"""

import geopandas as gpd
from shapely.geometry import Point

from core.utilities import time_function


@time_function
def convert_to_geo_dataframe(df):
    """
    Convert a pandas DataFrame with x,y coordinates to a GeoDataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame containing 'x' and 'y' coordinate columns.
        
    Returns:
        gpd.GeoDataFrame: GeoDataFrame with Point geometries created from x,y coordinates.
        
    Raises:
        KeyError: If 'x' or 'y' columns are not found in the DataFrame.
        ValueError: If coordinate data is invalid.
    """
    import logging
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    # Validate coordinate columns exist
    if 'x' not in df.columns or 'y' not in df.columns:
        missing_cols = [col for col in ['x', 'y'] if col not in df.columns]
        raise KeyError(f"Missing coordinate columns: {missing_cols}")
    
    # Check for missing coordinates
    missing_coords = df[['x', 'y']].isna().any(axis=1)
    if missing_coords.any():
        missing_count = missing_coords.sum()
        logger.warning(f"Found {missing_count} grid elements with missing coordinates")
        df = df.dropna(subset=['x', 'y'])
        logger.info(f"Removed {missing_count} elements. Proceeding with {len(df)} valid elements")
    
    # Check for invalid coordinates (e.g., zeros in projected systems)
    zero_coords = (df['x'] == 0) & (df['y'] == 0)
    if zero_coords.any():
        zero_count = zero_coords.sum()
        logger.warning(f"Found {zero_count} grid elements with (0, 0) coordinates")
    
    try:
        geometry = [Point(xy) for xy in zip(df.x, df.y)]
        geo_df = gpd.GeoDataFrame(df, geometry=geometry)
        logger.info(f"Successfully created GeoDataFrame with {len(geo_df)} features")
        return geo_df
    except Exception as e:
        logger.error(f"Error creating geometries: {e}")
        raise ValueError(f"Failed to create point geometries: {e}")

@time_function
def calculate_cell_size(geo_df):
    """
    Calculate the cell size based on the distance between the first two points.
    
    Args:
        geo_df (gpd.GeoDataFrame): GeoDataFrame with Point geometries.
        
    Returns:
        float: Distance between the first two points in the GeoDataFrame.
        
    Raises:
        ValueError: If the GeoDataFrame contains fewer than two points.
    """
    if len(geo_df) < 2:
        raise ValueError("The GeoDataFrame should contain at least two points.")
    point1 = geo_df.geometry.iloc[0]
    point2 = geo_df.geometry.iloc[1]
    cell_size = point1.distance(point2)
    return cell_size

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
    """
    geometry = [Point(xy) for xy in zip(df.x, df.y)]
    geo_df = gpd.GeoDataFrame(df, geometry=geometry)
    return geo_df

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

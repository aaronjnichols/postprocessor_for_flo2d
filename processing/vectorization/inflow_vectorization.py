"""Inflow node vectorization module.

This module creates point vector files for inflow nodes using hydrograph data
from ``INFLOW.DAT``. The resulting vector contains the inflow node grid ID,
maximum discharge, and time to peak in its attribute table.
"""

# Standard library imports
import os
import logging

# Third-party imports
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Local application imports
from core.utilities import time_function
from core.constants import (
    GRID_ID,
    X_COORD,
    Y_COORD,
    MAX_DISCHARGE,
    TIME_TO_PEAK,
)


@time_function
def create_inflow_points(
    inflow_data: pd.DataFrame,
    model_data: pd.DataFrame,
    coord_system: int,
    output_path: str,
    output_format: str = "Shapefile",
) -> str:
    """Create a vector file of inflow nodes with peak attributes.

    Args:
        inflow_data (pd.DataFrame): Hydrograph data with time as index and
            grid IDs as columns.
        model_data (pd.DataFrame): DataFrame with ``grid_id``, ``x`` and ``y``
            coordinates.
        coord_system (int): EPSG code for spatial reference.
        output_path (str): Directory to save the output file.
        output_format (str, optional): ``"Shapefile"`` or ``"GeoPackage"``.
            Defaults to ``"Shapefile"``.

    Returns:
        str: Path to the created shapefile or geopackage.
    """
    logger = logging.getLogger("FLO2D_Postprocessor")

    if inflow_data is None or inflow_data.empty:
        logger.warning("No inflow hydrograph data provided. Skipping shapefile creation.")
        return None

    # Calculate peak discharge and time to peak for each inflow node
    # Time index is already in hours; do not scale
    max_discharge = inflow_data.max()
    time_to_peak = inflow_data.idxmax()

    summary_df = pd.DataFrame({
        GRID_ID: max_discharge.index.astype(int),
        MAX_DISCHARGE: max_discharge.values,
        TIME_TO_PEAK: time_to_peak.values,
    })

    # Merge coordinates from model_data
    if {GRID_ID, X_COORD, Y_COORD}.issubset(model_data.columns):
        logger.info(f"Merging coordinates for {len(summary_df)} inflow nodes")
        logger.info(f"Model data grid ID range: {model_data[GRID_ID].min()} to {model_data[GRID_ID].max()}")
        logger.info(f"Inflow grid ID range: {summary_df[GRID_ID].min()} to {summary_df[GRID_ID].max()}")
        
        summary_df = pd.merge(summary_df, model_data[[GRID_ID, X_COORD, Y_COORD]], on=GRID_ID, how="left")
        
        # Validate coordinate merging results
        missing_coords = summary_df[[X_COORD, Y_COORD]].isna().any(axis=1)
        if missing_coords.any():
            missing_ids = summary_df.loc[missing_coords, GRID_ID].tolist()
            logger.warning(f"Missing coordinates for {missing_coords.sum()} inflow nodes with grid IDs: {missing_ids}")
            logger.warning("These nodes will be skipped in the output shapefile")
            
            # Remove nodes with missing coordinates
            summary_df = summary_df.dropna(subset=[X_COORD, Y_COORD])
            if summary_df.empty:
                logger.error("No inflow nodes have valid coordinates after merging")
                return None
        else:
            logger.info("All inflow nodes successfully matched with coordinates")
    else:
        missing = {GRID_ID, X_COORD, Y_COORD} - set(model_data.columns)
        logger.error(f"Model data missing required columns: {missing}")
        raise KeyError(f"Model data missing required columns: {missing}")

    # Validate coordinate values
    invalid_coords = (summary_df[X_COORD] == 0) & (summary_df[Y_COORD] == 0)
    if invalid_coords.any():
        invalid_ids = summary_df.loc[invalid_coords, GRID_ID].tolist()
        logger.warning(f"Found {invalid_coords.sum()} inflow nodes with (0, 0) coordinates: {invalid_ids}")
        summary_df = summary_df.loc[~invalid_coords]

    # Add 1-based display grid id
    if GRID_ID in summary_df.columns:
        summary_df['flo2d_grid_id'] = summary_df[GRID_ID] + 1

    # Create geometry
    try:
        geometry = [Point(xy) for xy in zip(summary_df[X_COORD], summary_df[Y_COORD])]
        gdf = gpd.GeoDataFrame(summary_df, geometry=geometry, crs=f"EPSG:{coord_system}")
        logger.info(f"Created GeoDataFrame with {len(gdf)} inflow points")
    except Exception as e:
        logger.error(f"Error creating point geometries: {e}")
        raise

    if gdf.empty:
        logger.warning("Inflow GeoDataFrame is empty. Nothing to save.")
        return None

    # Reorder to surface display id
    # Hide internal 0-based id; surface 1-based display id first
    ordered_cols = [c for c in ['flo2d_grid_id', MAX_DISCHARGE, TIME_TO_PEAK, X_COORD, Y_COORD] if c in gdf.columns]
    other_cols = [c for c in gdf.columns if c not in ordered_cols + [GRID_ID, 'geometry']]
    gdf = gdf[ordered_cols + other_cols + ['geometry']]

    if output_format == "Shapefile":
        output_file = os.path.join(output_path, "inflow_nodes.shp")
        try:
            gdf.to_file(output_file, driver="ESRI Shapefile", crs=f"EPSG:{coord_system}")
            logger.info(f"Inflow nodes Shapefile created at: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create Shapefile: {e}")
            raise
    elif output_format == "GeoPackage":
        output_file = os.path.join(output_path, "inflow_nodes.gpkg")
        try:
            if gdf.crs is None:
                gdf.crs = f"EPSG:{coord_system}"
            gdf.to_file(output_file, driver="GPKG")
            logger.info(f"Inflow nodes GeoPackage created at: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create GeoPackage: {e}")
            raise
    else:
        logger.error(
            f"Unsupported output format: {output_format}. Expected 'Shapefile' or 'GeoPackage'."
        )
        raise ValueError(f"Unsupported output format: {output_format}")

    return output_file

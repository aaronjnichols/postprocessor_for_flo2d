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
    time_scale: float = 10.0,
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
        time_scale (float, optional): Factor to scale the time index to hours.
            Defaults to ``10.0``.

    Returns:
        str: Path to the created shapefile or geopackage.
    """
    logger = logging.getLogger("FLO2D_Postprocessor")

    if inflow_data is None or inflow_data.empty:
        logger.warning("No inflow hydrograph data provided. Skipping shapefile creation.")
        return None

    # Calculate peak discharge and time to peak for each inflow node
    max_discharge = inflow_data.max()
    time_to_peak = inflow_data.idxmax() * time_scale

    summary_df = pd.DataFrame({
        GRID_ID: max_discharge.index.astype(int),
        MAX_DISCHARGE: max_discharge.values,
        TIME_TO_PEAK: time_to_peak.values,
    })

    # Merge coordinates from model_data
    if {GRID_ID, X_COORD, Y_COORD}.issubset(model_data.columns):
        summary_df = pd.merge(summary_df, model_data[[GRID_ID, X_COORD, Y_COORD]], on=GRID_ID, how="left")
    else:
        missing = {GRID_ID, X_COORD, Y_COORD} - set(model_data.columns)
        logger.error(f"Model data missing required columns: {missing}")
        raise KeyError(f"Model data missing required columns: {missing}")

    # Create geometry
    geometry = [Point(xy) for xy in zip(summary_df[X_COORD], summary_df[Y_COORD])]
    gdf = gpd.GeoDataFrame(summary_df, geometry=geometry, crs=f"EPSG:{coord_system}")

    if gdf.empty:
        logger.warning("Inflow GeoDataFrame is empty. Nothing to save.")
        return None

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

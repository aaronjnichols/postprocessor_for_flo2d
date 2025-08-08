"""Outflow node vectorization module.

This module creates point vector files for outflow nodes using hydrograph data
from ``OUTNQ.OUT`` and outflow codes from ``OUTFLOW.DAT``. The resulting vector 
contains the outflow node grid ID, outflow code, maximum discharge, and time to 
peak in its attribute table.
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
    OUTFLOW_CODE,
)


@time_function
def create_outflow_points(
    outflow_hydrograph_data: pd.DataFrame,
    outflow_grid_data: pd.DataFrame,
    model_data: pd.DataFrame,
    coord_system: int,
    output_path: str,
    output_format: str = "Shapefile",
    time_scale: float = 10.0,
) -> str:
    """Create a vector file of outflow nodes with peak attributes and outflow codes.

    Args:
        outflow_hydrograph_data (pd.DataFrame): Hydrograph data with time as index and
            grid IDs as columns from OUTNQ.OUT.
        outflow_grid_data (pd.DataFrame): DataFrame with outflow codes and grid IDs
            from OUTFLOW.DAT.
        model_data (pd.DataFrame): DataFrame with ``grid_id``, ``x`` and ``y``
            coordinates.
        coord_system (int): EPSG code for spatial reference.
        output_path (str): Directory to save the output file.
        output_format (str, optional): ``"Shapefile"`` or ``"GeoPackage"``.
            Defaults to ``"Shapefile"``.
        time_scale (float, optional): Factor to scale the time index to hours.
            Defaults to ``10.0``.

    Returns:
        str: Path to the created shapefile or geopackage, or None if creation failed.
    """
    logger = logging.getLogger("FLO2D_Postprocessor")

    if outflow_hydrograph_data is None or outflow_hydrograph_data.empty:
        logger.warning("No outflow hydrograph data provided. Skipping shapefile creation.")
        return None

    if outflow_grid_data is None or outflow_grid_data.empty:
        logger.warning("No outflow grid data provided. Skipping shapefile creation.")
        return None

    # Calculate peak discharge and time to peak for each outflow node
    max_discharge = outflow_hydrograph_data.max()
    time_to_peak = outflow_hydrograph_data.idxmax() * time_scale

    # Create summary dataframe from hydrograph data
    summary_df = pd.DataFrame({
        GRID_ID: max_discharge.index.astype(int),
        MAX_DISCHARGE: max_discharge.values,
        TIME_TO_PEAK: time_to_peak.values,
    })

    # Merge with outflow codes from OUTFLOW.DAT
    # Convert grid_id in outflow_grid_data to int for proper merging
    outflow_grid_data = outflow_grid_data.copy()
    outflow_grid_data[GRID_ID] = pd.to_numeric(outflow_grid_data[GRID_ID], errors='coerce').astype('Int64')
    
    summary_df = pd.merge(
        summary_df, 
        outflow_grid_data[[GRID_ID, OUTFLOW_CODE]], 
        on=GRID_ID, 
        how="left"
    )

    # Fill missing outflow codes with 'O' as default
    summary_df[OUTFLOW_CODE] = summary_df[OUTFLOW_CODE].fillna('O')

    # Merge coordinates from model_data
    if {GRID_ID, X_COORD, Y_COORD}.issubset(model_data.columns):
        summary_df = pd.merge(summary_df, model_data[[GRID_ID, X_COORD, Y_COORD]], on=GRID_ID, how="left")
    else:
        missing = {GRID_ID, X_COORD, Y_COORD} - set(model_data.columns)
        logger.error(f"Model data missing required columns: {missing}")
        raise KeyError(f"Model data missing required columns: {missing}")

    # Check if we have valid coordinates
    valid_coords = summary_df[[X_COORD, Y_COORD]].notna().all(axis=1)
    if not valid_coords.any():
        logger.warning("No valid coordinates found for outflow nodes. Cannot create vector file.")
        return None

    # Filter to only rows with valid coordinates
    if not valid_coords.all():
        missing_count = (~valid_coords).sum()
        logger.warning(f"Excluding {missing_count} outflow nodes with missing coordinates")
        summary_df = summary_df[valid_coords]

    # Create geometry
    geometry = [Point(xy) for xy in zip(summary_df[X_COORD], summary_df[Y_COORD])]
    gdf = gpd.GeoDataFrame(summary_df, geometry=geometry, crs=f"EPSG:{coord_system}")

    if gdf.empty:
        logger.warning("Outflow GeoDataFrame is empty. Nothing to save.")
        return None

    # Save the vector file
    if output_format == "Shapefile":
        output_file = os.path.join(output_path, "outflow_nodes.shp")
        try:
            gdf.to_file(output_file, driver="ESRI Shapefile")
            logger.info(f"Outflow nodes Shapefile created at: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create Shapefile: {e}")
            raise
    elif output_format == "GeoPackage":
        output_file = os.path.join(output_path, "outflow_nodes.gpkg")
        try:
            if gdf.crs is None:
                gdf.crs = f"EPSG:{coord_system}"
            gdf.to_file(output_file, driver="GPKG")
            logger.info(f"Outflow nodes GeoPackage created at: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create GeoPackage: {e}")
            raise
    else:
        logger.error(
            f"Unsupported output format: {output_format}. Expected 'Shapefile' or 'GeoPackage'."
        )
        raise ValueError(f"Unsupported output format: {output_format}")

    logger.info(f"Created outflow vector file with {len(gdf)} nodes")
    return output_file 
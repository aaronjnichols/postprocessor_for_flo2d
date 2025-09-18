# hystruc_vectorization.py

import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import LineString
import os
from core.utilities import time_function
import logging
from core.constants import INFLOW_NODE, OUTFLOW_NODE, GRID_ID, STRUCTURE_ID
from extraction.out.hydrostruct_out_extraction import extract_hydrostruct_out

@time_function
def create_hystruc_shapefile(hystruc_df, model_data_df, coord_system, folder_path, output_path, output_format="Shapefile"):
    """
    Create a shapefile or geopackage for hydraulic structures based on the specified output format.

    Args:
        hystruc_df (DataFrame): Hydraulic structures data.
        model_data_df (DataFrame): Model data with 'grid_id', 'x', 'y' columns.
        coord_system (int): EPSG code for spatial reference.
        folder_path (str): Path to the FLO-2D project directory (for HYDROSTRUCT.OUT).
        output_path (str): Directory path to save the output file.
        output_format (str): Desired output format ("Shapefile" or "GeoPackage").

    Returns:
        str: Path to the created shapefile or geopackage.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')

    # Merge peak discharge information from HYDROSTRUCT.OUT if available
    try:
        hydrostruct_data = extract_hydrostruct_out(folder_path)
        peaks_df = hydrostruct_data['peaks']
        hystruc_df = pd.merge(hystruc_df, peaks_df, on=STRUCTURE_ID, how='left')
    except FileNotFoundError:
        logger.warning(f"HYDROSTRUCT.OUT not found in {folder_path}. Skipping peak merge.")

    # Merge the hystruc dataframe with the model data dataframe to get x, y coordinates for inflow and outflow nodes
    # This assumes the model_data_df has 'grid_id', 'x', 'y' columns
    merged_df = pd.merge(hystruc_df, model_data_df[[GRID_ID, 'x', 'y']], left_on=INFLOW_NODE, right_on=GRID_ID, how='left')
    merged_df.rename(columns={'x': 'inflow_x', 'y': 'inflow_y'}, inplace=True)
    merged_df = pd.merge(merged_df, model_data_df[[GRID_ID, 'x', 'y']], left_on=OUTFLOW_NODE, right_on=GRID_ID, how='left', suffixes=('', '_outflow'))
    merged_df.rename(columns={'x': 'outflow_x', 'y': 'outflow_y'}, inplace=True)

    # Add 1-based display IDs
    if INFLOW_NODE in merged_df.columns:
        merged_df['inflow_grid_id'] = merged_df[INFLOW_NODE] + 1
    if OUTFLOW_NODE in merged_df.columns:
        merged_df['outflow_grid_id'] = merged_df[OUTFLOW_NODE] + 1

    # Drop internal 0-based id columns to avoid clutter in user-facing output
    cols_to_drop = []
    if GRID_ID in merged_df.columns:
        cols_to_drop.append(GRID_ID)
    if f"{GRID_ID}_outflow" in merged_df.columns:
        cols_to_drop.append(f"{GRID_ID}_outflow")
    if INFLOW_NODE in merged_df.columns:
        cols_to_drop.append(INFLOW_NODE)
    if OUTFLOW_NODE in merged_df.columns:
        cols_to_drop.append(OUTFLOW_NODE)
    if cols_to_drop:
        merged_df = merged_df.drop(columns=[c for c in cols_to_drop if c in merged_df.columns])

    # Vectorized creation of LineString geometries
    valid = ~merged_df[['inflow_x', 'inflow_y', 'outflow_x', 'outflow_y']].isna().any(axis=1)
    coords = merged_df.loc[valid, ['inflow_x', 'inflow_y', 'outflow_x', 'outflow_y']].to_numpy()
    geometry = [LineString([(x1, y1), (x2, y2)]) for x1, y1, x2, y2 in coords]

    gdf = gpd.GeoDataFrame(merged_df.loc[valid].copy(), geometry=geometry, crs=f"EPSG:{coord_system}")

    if gdf.empty:
        logger.warning("No Hydraulic Structures data to save. GeoDataFrame is empty.")
        return None

    # Reorder columns to surface display IDs if present
    # Surface 1-based display ids first (internal ids were dropped already)
    display_cols = [c for c in ['inflow_grid_id', 'outflow_grid_id'] if c in gdf.columns]
    other_cols = [c for c in gdf.columns if c not in display_cols + ['geometry']]
    gdf = gdf[display_cols + other_cols + ['geometry']]

    if output_format == "Shapefile":
        output_file = os.path.join(output_path, 'hydraulic_structures.shp')
        try:
            if gdf.crs is None:
                gdf = gdf.set_crs(f"EPSG:{coord_system}")
            gdf.to_file(output_file, driver="ESRI Shapefile")
            logger.info(f"Hydraulic Structures Shapefile created at: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create Shapefile: {str(e)}")
            raise
    elif output_format == "GeoPackage":
        output_file = os.path.join(output_path, 'hydraulic_structures.gpkg')
        try:
            if gdf.crs is None:
                gdf = gdf.set_crs(f"EPSG:{coord_system}")
            gdf.to_file(output_file, driver="GPKG")
            logger.info(f"Hydraulic Structures GeoPackage created at: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create GeoPackage: {str(e)}")
            raise
    else:
        logger.error(f"Unsupported output format: {output_format}. Expected 'Shapefile' or 'GeoPackage'.")
        raise ValueError(f"Unsupported output format: {output_format}")

    return output_file

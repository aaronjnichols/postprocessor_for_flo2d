"""
SWMM Vectorization Module

This module handles the creation of shapefiles and geopackages from SWMM data.
Separated from extraction logic for better code organization.
"""

import os
import logging
import pandas as pd
from core.utilities import time_function
from core.constants import NODE_ID, LINK_ID


def save_geodataframe(gdf, output_path, layer_name, coord_system, output_format, logger):
    """
    Save the GeoDataFrame to the specified format (Shapefile or GeoPackage).

    Args:
        gdf (GeoDataFrame): The GeoDataFrame to save.
        output_path (str): Base path to save the file.
        layer_name (str): Name of the layer/file.
        coord_system (int): EPSG code for the coordinate system.
        output_format (str): "Shapefile" or "GeoPackage".
        logger (logging.Logger): Logger instance.
    
    Returns:
        str: Path to the saved file.
    """

    if output_format == "Shapefile":
        output_file = os.path.join(output_path, f'{layer_name}.shp')
        try:
            gdf.to_file(output_file, driver="ESRI Shapefile", crs=f"EPSG:{coord_system}")
            logger.info(f"SWMM {layer_name.capitalize()} Shapefile created at: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create Shapefile for {layer_name}: {str(e)}")
            raise
    elif output_format == "GeoPackage":
        output_file = os.path.join(output_path, f'swmm_{layer_name}.gpkg')
        try:
            # Ensure CRS is set on GeoDataFrame before saving (pyogrio engine doesn't support crs parameter)
            if gdf.crs is None:
                gdf.crs = f"EPSG:{coord_system}"
            gdf.to_file(output_file, layer=layer_name, driver="GPKG")
            logger.info(f"SWMM {layer_name.capitalize()} GeoPackage created at: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create GeoPackage for {layer_name}: {str(e)}")
            raise
    else:
        logger.error(f"Unsupported output format: {output_format}. Expected 'Shapefile' or 'GeoPackage'.")
        raise ValueError(f"Unsupported output format: {output_format}")

    return output_file


def _merge_rpt_summary_data(gdf, summary_df, id_column, feature_type):
    """
    Merge RPT summary data with SWMM geometry data.
    
    Args:
        gdf (GeoDataFrame): Original SWMM geometry data
        summary_df (DataFrame): Summary data from RPT extraction
        id_column (str): Column name for ID matching (NODE_ID or LINK_ID)
        feature_type (str): Type of feature for logging ('junctions', 'outfalls', 'conduits')
    
    Returns:
        GeoDataFrame: Enhanced GeoDataFrame with RPT summary data
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if gdf.empty or summary_df is None or summary_df.empty:
        logger.info(f"No RPT summary data available for {feature_type}")
        return gdf
    
    # Check if ID column exists in both dataframes
    if id_column not in gdf.columns:
        logger.warning(f"ID column '{id_column}' not found in {feature_type} geometry data")
        return gdf
    
    if id_column not in summary_df.columns:
        logger.warning(f"ID column '{id_column}' not found in {feature_type} summary data")
        return gdf
    
    # Merge the dataframes
    try:
        merged_gdf = gdf.merge(summary_df, on=id_column, how='left', suffixes=('', '_rpt'))
        logger.info(f"Successfully merged RPT summary data for {len(merged_gdf)} {feature_type}")
        
        # Log which features got RPT data
        rpt_data_count = merged_gdf[summary_df.columns.difference([id_column])].notna().any(axis=1).sum()
        logger.info(f"{rpt_data_count} out of {len(merged_gdf)} {feature_type} have RPT summary data")
        
        return merged_gdf
    except Exception as e:
        logger.error(f"Failed to merge RPT summary data for {feature_type}: {str(e)}")
        return gdf


@time_function
def create_swmm_shapefiles(swmm_data, output_path, output_format="Shapefile", 
                          nodes_summary=None, links_summary=None):
    """
    Creates shapefiles or geopackages for SWMM junctions, conduits, and outfalls.
    Optionally merges RPT summary data into the attribute tables.

    Parameters:
    - swmm_data: dict of GeoDataFrames from extract_swmm_inp
    - output_path: str, path to save the shapefiles or geopackages
    - output_format: str, "Shapefile" or "GeoPackage"
    - nodes_summary: DataFrame, optional summary data for nodes from RPT extraction
    - links_summary: DataFrame, optional summary data for links from RPT extraction

    Returns:
    - list of created file paths
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    shapefile_paths = []

    if 'junctions' in swmm_data:
        junctions_gdf = swmm_data['junctions']
        if not junctions_gdf.empty:
            # Merge RPT summary data for junctions
            enhanced_junctions = _merge_rpt_summary_data(
                junctions_gdf, nodes_summary, NODE_ID, 'junctions'
            )
            shp_path = save_geodataframe(enhanced_junctions, output_path, 'junctions', 
                                       enhanced_junctions.crs.to_epsg(), output_format, logger)
            shapefile_paths.append(shp_path)
        else:
            logger.warning("No junctions data to save.")

    if 'outfalls' in swmm_data:
        outfalls_gdf = swmm_data['outfalls']
        if not outfalls_gdf.empty:
            # Merge RPT summary data for outfalls
            enhanced_outfalls = _merge_rpt_summary_data(
                outfalls_gdf, nodes_summary, NODE_ID, 'outfalls'
            )
            shp_path = save_geodataframe(enhanced_outfalls, output_path, 'outfalls', 
                                       enhanced_outfalls.crs.to_epsg(), output_format, logger)
            shapefile_paths.append(shp_path)
        else:
            logger.warning("No outfalls data to save.")

    if 'conduits' in swmm_data:
        conduits_gdf = swmm_data['conduits']
        if not conduits_gdf.empty:
            # Merge RPT summary data for conduits
            enhanced_conduits = _merge_rpt_summary_data(
                conduits_gdf, links_summary, LINK_ID, 'conduits'
            )
            shp_path = save_geodataframe(enhanced_conduits, output_path, 'conduits', 
                                       enhanced_conduits.crs.to_epsg(), output_format, logger)
            shapefile_paths.append(shp_path)
        else:
            logger.warning("No conduits data to save.")

    return shapefile_paths


if __name__ == "__main__":
    import sys
    from extraction.dat.swmm_inp_extraction import extract_swmm_inp

    if len(sys.argv) < 4:
        print("Usage: python swmm_vectorization.py <path_to_swmm_file> <epsg_code> <output_format>")
        sys.exit(1)

    file_path = sys.argv[1]
    epsg = int(sys.argv[2])
    output_format = sys.argv[3].capitalize()

    # Validate output_format
    if output_format not in ["Shapefile", "Geopackage"]:
        print("Output format must be 'Shapefile' or 'GeoPackage'.")
        sys.exit(1)

    swmm_data = extract_swmm_inp(file_path, epsg)

    output_path = os.path.dirname(file_path)
    shapefile_paths = create_swmm_shapefiles(swmm_data, output_path, output_format)

    print("Created files:", shapefile_paths)
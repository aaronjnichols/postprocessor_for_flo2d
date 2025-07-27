"""
SWMM Vectorization Module

This module handles the creation of shapefiles and geopackages from SWMM data.
Separated from extraction logic for better code organization.
"""

import os
import logging
from core.utilities import time_function


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


@time_function
def create_swmm_shapefiles(swmm_data, output_path, output_format="Shapefile"):
    """
    Creates shapefiles or geopackages for SWMM junctions, conduits, and outfalls.

    Parameters:
    - swmm_data: dict of GeoDataFrames from extract_swmm_data
    - output_path: str, path to save the shapefiles or geopackages
    - output_format: str, "Shapefile" or "GeoPackage"

    Returns:
    - list of created file paths
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    shapefile_paths = []

    if 'junctions' in swmm_data:
        junctions_gdf = swmm_data['junctions']
        if not junctions_gdf.empty:
            shp_path = save_geodataframe(junctions_gdf, output_path, 'junctions', junctions_gdf.crs.to_epsg(), output_format, logger)
            shapefile_paths.append(shp_path)
        else:
            logger.warning("No junctions data to save.")

    if 'outfalls' in swmm_data:
        outfalls_gdf = swmm_data['outfalls']
        if not outfalls_gdf.empty:
            shp_path = save_geodataframe(outfalls_gdf, output_path, 'outfalls', outfalls_gdf.crs.to_epsg(), output_format, logger)
            shapefile_paths.append(shp_path)
        else:
            logger.warning("No outfalls data to save.")

    if 'conduits' in swmm_data:
        conduits_gdf = swmm_data['conduits']
        if not conduits_gdf.empty:
            shp_path = save_geodataframe(conduits_gdf, output_path, 'conduits', conduits_gdf.crs.to_epsg(), output_format, logger)
            shapefile_paths.append(shp_path)
        else:
            logger.warning("No conduits data to save.")

    return shapefile_paths


if __name__ == "__main__":
    import sys
    from extraction.dat.swmm_dat_extraction import extract_swmm_data

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

    swmm_data = extract_swmm_data(file_path, epsg)

    output_path = os.path.dirname(file_path)
    shapefile_paths = create_swmm_shapefiles(swmm_data, output_path, output_format)

    print("Created files:", shapefile_paths)
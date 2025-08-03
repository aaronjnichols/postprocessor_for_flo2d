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
from shapely.geometry import MultiLineString
from shapely import ops

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

    ux = np.sort(model_geo_df[X_COORD].unique())
    uy = np.sort(model_geo_df[Y_COORD].unique())

    if len(ux) < 2 or len(uy) < 2:
        logger.error("Insufficient unique coordinates to determine grid spacing")
        return None

    dx = np.diff(ux)
    dy = np.diff(uy)
    cell = (np.median(dx) + np.median(dy)) / 2.0
    half = cell / 2.0

    xi = np.searchsorted(ux, model_geo_df[X_COORD].values)
    yi = np.searchsorted(uy, model_geo_df[Y_COORD].values)
    mask = np.zeros((len(uy), len(ux)), dtype=bool)
    mask[yi, xi] = True

    left = mask & ~np.roll(mask, 1, axis=1)
    left[:, 0] = mask[:, 0]
    right = mask & ~np.roll(mask, -1, axis=1)
    right[:, -1] = mask[:, -1]
    bottom = mask & ~np.roll(mask, 1, axis=0)
    bottom[0, :] = mask[0, :]
    top = mask & ~np.roll(mask, -1, axis=0)
    top[-1, :] = mask[-1, :]

    def edge_segments(boundary_mask, orient):
        idx = np.argwhere(boundary_mask)
        segs = []
        if orient == "left":
            for r, c in idx:
                x = ux[c] - half
                y0, y1 = uy[r] - half, uy[r] + half
                segs.append(((x, y0), (x, y1)))
        elif orient == "right":
            for r, c in idx:
                x = ux[c] + half
                y0, y1 = uy[r] - half, uy[r] + half
                segs.append(((x, y0), (x, y1)))
        elif orient == "bottom":
            for r, c in idx:
                y = uy[r] - half
                x0, x1 = ux[c] - half, ux[c] + half
                segs.append(((x0, y), (x1, y)))
        else:  # top
            for r, c in idx:
                y = uy[r] + half
                x0, x1 = ux[c] - half, ux[c] + half
                segs.append(((x0, y), (x1, y)))
        return segs

    edges = []
    edges.extend(edge_segments(left, "left"))
    edges.extend(edge_segments(right, "right"))
    edges.extend(edge_segments(bottom, "bottom"))
    edges.extend(edge_segments(top, "top"))

    perimeter_poly = next(ops.polygonize(MultiLineString(edges)), None)
    if perimeter_poly is None:
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


# swmm_extraction.py

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import os
import logging
import re
from core.utilities import time_function
from core.constants import (
    SWMM_NAME, INVERT_ELEVATION, MAX_DEPTH, INIT_DEPTH, SURCHARGE_DEPTH, PONDED_AREA,
    OUTFALL_TYPE, STAGE_DATA, TIDE_GATE, FROM_NODE, TO_NODE, LENGTH, MANNINGS_N,
    INLET_OFFSET, OUTLET_OFFSET, INIT_FLOW, MAX_FLOW, X_COORD, Y_COORD
)

def extract_swmm_inp(file_path, epsg):
    """
    Extracts SWMM data from an input file and returns processed GeoDataFrames.

    Parameters:
    - file_path: str, path to the SWMM .inp file.
    - epsg: int, EPSG code for the coordinate reference system.

    Returns:
    - dict of GeoDataFrames for junctions, outfalls, and conduits.
    """
    sections = {
        'JUNCTIONS': [], 'OUTFALLS': [], 'CONDUITS': [], 'XSECTIONS': [],
        'COORDINATES': [], 'LOSSES': [], 'INFLOWS': []
    }

    current_section = None

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            # Identify section headers
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1].upper()
                continue
            if not line or line.startswith(';'):  # Skip empty lines and comments
                continue
            # Only extract data for relevant sections
            if current_section in sections:
                sections[current_section].append(line)

    results = {}
    if sections['JUNCTIONS']:
        results['junctions'] = _process_junctions(sections['JUNCTIONS'], sections['COORDINATES'], epsg)
    if sections['OUTFALLS']:
        results['outfalls'] = _process_outfalls(sections['OUTFALLS'], sections['COORDINATES'], epsg)
    if sections['CONDUITS']:
        results['conduits'] = _process_conduits(
            sections['CONDUITS'], sections['XSECTIONS'], sections.get('LOSSES', []), sections['COORDINATES'], epsg
        )

    return results

def _process_junctions(junctions_data, coordinates_data, coord_system):
    """
    Processes the junctions data into a GeoDataFrame using the coordinates from the COORDINATES section.

    Parameters:
    - junctions_data: List of junction data lines.
    - coordinates_data: List of coordinates data lines.
    - coord_system: EPSG code for the coordinate reference system.

    Returns:
    - GeoDataFrame with junction points.
    """
    columns = [SWMM_NAME, INVERT_ELEVATION, MAX_DEPTH, INIT_DEPTH, SURCHARGE_DEPTH, PONDED_AREA]
    junctions = []

    for line in junctions_data:
        parts = re.split(r'\s+', line.strip())
        if len(parts) < len(columns):
            parts += [None] * (len(columns) - len(parts))  # Pad missing values with None
        junctions.append(parts[:len(columns)])

    df_junctions = pd.DataFrame(junctions, columns=columns)
    df_junctions = df_junctions.apply(pd.to_numeric, errors='ignore')

    coords_columns = [SWMM_NAME, X_COORD, Y_COORD]
    coords = []

    for line in coordinates_data:
        parts = re.split(r'\s+', line.strip())
        if len(parts) < len(coords_columns):
            parts += [None] * (len(coords_columns) - len(parts))
        coords.append(parts[:len(coords_columns)])

    df_coords = pd.DataFrame(coords, columns=coords_columns)
    df_coords[[X_COORD, Y_COORD]] = df_coords[[X_COORD, Y_COORD]].apply(pd.to_numeric, errors='coerce')

    df_merged = pd.merge(df_junctions, df_coords, on=SWMM_NAME, how='left')
    geometry = [Point(xy) for xy in zip(df_merged[X_COORD], df_merged[Y_COORD])]
    gdf = gpd.GeoDataFrame(df_merged, geometry=geometry, crs=f"EPSG:{coord_system}")

    return gdf

def _process_outfalls(outfalls_data, coordinates_data, coord_system):
    """
    Processes the outfalls data into a GeoDataFrame using the coordinates from the COORDINATES section.

    Parameters:
    - outfalls_data: List of outfalls data lines.
    - coordinates_data: List of coordinates data lines.
    - coord_system: EPSG code for the coordinate reference system.

    Returns:
    - GeoDataFrame with outfall points.
    """
    columns = [SWMM_NAME, 'Invert_Elevation', 'Outfall_Type', 'Stage_Data', 'Tide_Gate']
    outfalls = []

    for line in outfalls_data:
        parts = re.split(r'\s+', line.strip())
        if len(parts) < len(columns):
            parts += [None] * (len(columns) - len(parts))  # Pad missing values with None
        outfalls.append(parts[:len(columns)])

    df_outfalls = pd.DataFrame(outfalls, columns=columns)
    df_outfalls = df_outfalls.apply(pd.to_numeric, errors='ignore')

    coords_columns = [SWMM_NAME, X_COORD, Y_COORD]
    coords = []

    for line in coordinates_data:
        parts = re.split(r'\s+', line.strip())
        if len(parts) < len(coords_columns):
            parts += [None] * (len(coords_columns) - len(parts))
        coords.append(parts[:len(coords_columns)])

    df_coords = pd.DataFrame(coords, columns=coords_columns)
    df_coords[[X_COORD, Y_COORD]] = df_coords[[X_COORD, Y_COORD]].apply(pd.to_numeric, errors='coerce')

    df_merged = pd.merge(df_outfalls, df_coords, on=SWMM_NAME, how='left')
    geometry = [Point(xy) for xy in zip(df_merged[X_COORD], df_merged[Y_COORD])]
    gdf = gpd.GeoDataFrame(df_merged, geometry=geometry, crs=f"EPSG:{coord_system}")

    return gdf

def _process_conduits(conduits_data, xsections_data, losses_data, coordinates_data, coord_system):
    """
    Processes the conduits data into a GeoDataFrame using the coordinates from the COORDINATES section.

    Parameters:
    - conduits_data: List of conduits data lines.
    - xsections_data: List of cross-section data lines.
    - coordinates_data: List of coordinates data lines.
    - coord_system: EPSG code for the coordinate reference system.

    Returns:
    - GeoDataFrame with conduit lines.
    """
    conduit_columns = [SWMM_NAME, FROM_NODE, TO_NODE, LENGTH, 'Manning_N', INLET_OFFSET, OUTLET_OFFSET, INIT_FLOW, MAX_FLOW]
    conduits = []

    for line in conduits_data:
        parts = re.split(r'\s+', line.strip())
        if len(parts) < len(conduit_columns):
            parts += [None] * (len(conduit_columns) - len(parts))  # Pad missing values with None
        conduits.append(parts[:len(conduit_columns)])

    df_conduits = pd.DataFrame(conduits, columns=conduit_columns)
    df_conduits = df_conduits.apply(pd.to_numeric, errors='ignore')

    coords_columns = [SWMM_NAME, X_COORD, Y_COORD]
    coords = []

    for line in coordinates_data:
        parts = re.split(r'\s+', line.strip())
        if len(parts) < len(coords_columns):
            parts += [None] * (len(coords_columns) - len(parts))
        coords.append(parts[:len(coords_columns)])

    df_coords = pd.DataFrame(coords, columns=coords_columns)
    df_coords[[X_COORD, Y_COORD]] = df_coords[[X_COORD, Y_COORD]].apply(pd.to_numeric, errors='coerce')

    # Store the original conduit name column before merging (this is the conduit ID)
    conduit_names = df_conduits[SWMM_NAME].copy()
    
    # Merge conduit start (From_Node) and end (To_Node) coordinates
    # First merge: add FROM node coordinates
    df_merged_from = pd.merge(df_conduits, df_coords, left_on=FROM_NODE, right_on=SWMM_NAME, how='left', suffixes=('', '_from'))
    # Rename the coordinate columns to avoid conflicts in second merge
    # NOTE: We're renaming the SWMM_NAME from coords data, not the original conduit name
    df_merged_from = df_merged_from.rename(columns={
        f"{SWMM_NAME}_from": f"from_node_{SWMM_NAME}",  # This is the coordinate's name column
        X_COORD: f"{X_COORD}_from", 
        Y_COORD: f"{Y_COORD}_from"
    })
    
    # Second merge: add TO node coordinates  
    df_merged_to = pd.merge(df_merged_from, df_coords, left_on=TO_NODE, right_on=SWMM_NAME, how='left', suffixes=('', '_to'))
    # Rename the TO node coordinate columns for clarity
    df_merged_to = df_merged_to.rename(columns={
        f"{SWMM_NAME}_to": f"to_node_{SWMM_NAME}",  # This is the coordinate's name column
        X_COORD: f"{X_COORD}_to",
        Y_COORD: f"{Y_COORD}_to"
    })
    
    # Ensure the original conduit name column is preserved
    if SWMM_NAME not in df_merged_to.columns:
        df_merged_to[SWMM_NAME] = conduit_names
    
    # Remove duplicate columns if they exist
    columns_to_check = list(df_merged_to.columns)
    duplicate_cols = []
    for i, col in enumerate(columns_to_check):
        if columns_to_check.count(col) > 1:
            # Keep first occurrence, mark others for removal
            if col in columns_to_check[:i]:
                duplicate_cols.append(i)
    
    if duplicate_cols:
        # Remove duplicate columns by index
        df_merged_to = df_merged_to.iloc[:, [i for i in range(len(columns_to_check)) if i not in duplicate_cols]]

    # Parse XSECTIONS section and merge attributes
    xs_records = []
    for line in xsections_data or []:
        parts = re.split(r'\s+', line.strip())
        if len(parts) >= 7:
            rec = {
                SWMM_NAME: parts[0],
                'shape': parts[1],
                'geom1': parts[2] if len(parts) > 2 else None,
                'geom2': parts[3] if len(parts) > 3 else None,
                'geom3': parts[4] if len(parts) > 4 else None,
                'geom4': parts[5] if len(parts) > 5 else None,
                'barrels': parts[6] if len(parts) > 6 else None,
                'culvert': parts[7] if len(parts) > 7 else None,
            }
            xs_records.append(rec)
    if xs_records:
        df_xs = pd.DataFrame(xs_records)
        # Coerce numerics where applicable
        for c in ['geom1', 'geom2', 'geom3', 'geom4']:
            if c in df_xs.columns:
                df_xs[c] = pd.to_numeric(df_xs[c], errors='coerce')
        if 'barrels' in df_xs.columns:
            df_xs['barrels'] = pd.to_numeric(df_xs['barrels'], errors='coerce')
        df_merged_to = pd.merge(df_merged_to, df_xs, on=SWMM_NAME, how='left')

    # Parse LOSSES section and merge attributes
    losses_records = []
    for line in losses_data or []:
        parts = re.split(r'\s+', line.strip())
        if len(parts) >= 6:
            # LOSSES: link Inlet Outlet Average FlapGate Seepage
            rec = {
                SWMM_NAME: parts[0],
                'loss_inlet': parts[1],
                'loss_outlet': parts[2],
                'loss_avg': parts[3],
                'flap_gate': parts[4],
                'seepage': parts[5],
            }
            losses_records.append(rec)
    if losses_records:
        df_losses = pd.DataFrame(losses_records)
        # Coerce numeric loss coefficients where possible
        for c in ['loss_inlet', 'loss_outlet', 'loss_avg', 'seepage']:
            if c in df_losses.columns:
                df_losses[c] = pd.to_numeric(df_losses[c], errors='ignore')
        df_merged_to = pd.merge(df_merged_to, df_losses, on=SWMM_NAME, how='left')

    # Create LineString geometries for the conduits
    from_x_col = f"{X_COORD}_from"  # x_from
    from_y_col = f"{Y_COORD}_from"  # y_from
    to_x_col = f"{X_COORD}_to"      # x_to
    to_y_col = f"{Y_COORD}_to"      # y_to
    
    geometry = [
        LineString([
            (row[from_x_col], row[from_y_col]),
            (row[to_x_col], row[to_y_col])
        ]) for index, row in df_merged_to.iterrows()
        if not pd.isna(row[from_x_col]) and not pd.isna(row[to_x_col])
    ]

    gdf = gpd.GeoDataFrame(df_merged_to, geometry=geometry, crs=f"EPSG:{coord_system}")

    return gdf


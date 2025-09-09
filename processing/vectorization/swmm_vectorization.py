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
from processing.vectorization.swmm_schema import (
    apply_junction_schema,
    apply_outfall_schema,
    apply_link_schema,
)


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
            # Set CRS before saving to avoid pyogrio engine issues
            if gdf.crs is None:
                gdf.crs = f"EPSG:{coord_system}"
            gdf.to_file(output_file, driver="ESRI Shapefile")
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


def _clean_column_names(df):
    """
    Clean column names for better GIS format compatibility.
    Handles case-sensitivity conflicts and other naming issues.
    
    Args:
        df (DataFrame or GeoDataFrame): DataFrame with potentially problematic column names
        
    Returns:
        DataFrame or GeoDataFrame: DataFrame with cleaned column names
    """
    import re
    
    # Create a copy to avoid modifying the original
    cleaned_df = df.copy()
    
    # Dictionary to track renamed columns for logging
    renamed_columns = {}
    
    # First pass: handle case-sensitivity conflicts
    # Convert all column names to lowercase to detect conflicts
    lowercase_cols = {}
    for col in cleaned_df.columns:
        if col == 'geometry':
            continue  # Skip geometry column
        lowercase_key = col.lower()
        if lowercase_key in lowercase_cols:
            # We have a case conflict
            existing_col = lowercase_cols[lowercase_key]
            logger = logging.getLogger('FLO2D_Postprocessor')
            logger.info(f"Case conflict detected: '{existing_col}' vs '{col}' - renaming second one")
            # Rename the second occurrence
            new_name = f"{col}_alt"
            cleaned_df = cleaned_df.rename(columns={col: new_name})
            renamed_columns[col] = new_name
        else:
            lowercase_cols[lowercase_key] = col
    
    # Second pass: clean problematic characters and ensure format compliance
    new_column_names = {}
    for col in cleaned_df.columns:
        if col == 'geometry':
            new_column_names[col] = col
            continue  # Skip geometry column
            
        original_col = col
        
        # Replace problematic characters
        clean_col = re.sub(r'[^a-zA-Z0-9_]', '_', col)
        
        # Ensure it doesn't start with a number
        if clean_col and clean_col[0].isdigit():
            clean_col = f"col_{clean_col}"
        
        # Truncate if too long (some formats have limits)
        if len(clean_col) > 63:  # Most GIS formats support up to 64 characters
            clean_col = clean_col[:63]
        
        # Handle empty names
        if not clean_col or clean_col == '_':
            clean_col = f"field_{len(new_column_names)}"
        
        # Ensure uniqueness
        if clean_col in new_column_names.values():
            counter = 1
            base_name = clean_col[:60] if len(clean_col) > 60 else clean_col
            while f"{base_name}_{counter}" in new_column_names.values():
                counter += 1
            clean_col = f"{base_name}_{counter}"
        
        new_column_names[original_col] = clean_col
        
        if original_col != clean_col:
            renamed_columns[original_col] = clean_col
    
    if renamed_columns:
        logger = logging.getLogger('FLO2D_Postprocessor')
        logger.info(f"Cleaned {len(renamed_columns)} column names for GIS compatibility")
        for old, new in list(renamed_columns.items())[:5]:  # Show first 5 examples
            logger.info(f"  '{old}' -> '{new}'")
    
    # Rename columns
    cleaned_df = cleaned_df.rename(columns=new_column_names)
    
    return cleaned_df


def _merge_rpt_summary_data(gdf, summary_df, rpt_id_column, feature_type):
    """
    Merge RPT summary data with SWMM geometry data.
    
    Args:
        gdf (GeoDataFrame): Original SWMM geometry data
        summary_df (DataFrame): Summary data from RPT extraction
        rpt_id_column (str): Column name for ID matching in RPT data (NODE_ID or LINK_ID)
        feature_type (str): Type of feature for logging ('junctions', 'outfalls', 'conduits')
    
    Returns:
        GeoDataFrame: Enhanced GeoDataFrame with RPT summary data
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    # Import constants for column name mapping
    from core.constants import SWMM_NAME
    
    # Debug logging
    logger.info(f"=== MERGE DEBUG for {feature_type} ===")
    logger.info(f"GDF shape: {gdf.shape if not gdf.empty else 'EMPTY'}")
    logger.info(f"Summary DF shape: {summary_df.shape if summary_df is not None and not summary_df.empty else 'EMPTY/NONE'}")
    
    if gdf.empty or summary_df is None or summary_df.empty:
        logger.info(f"No RPT summary data available for {feature_type}")
        return gdf
    
    # Determine the geometry ID column (should be SWMM_NAME for all SWMM features)
    geometry_id_column = SWMM_NAME  # This is 'name'
    
    if not gdf.empty:
        logger.info(f"GDF columns: {list(gdf.columns)}")
        if geometry_id_column in gdf.columns:
            logger.info(f"GDF {geometry_id_column} sample: {gdf[geometry_id_column].head(3).tolist()}")
    
    if summary_df is not None and not summary_df.empty:
        logger.info(f"Summary DF columns: {list(summary_df.columns)}")
        if rpt_id_column in summary_df.columns:
            logger.info(f"Summary DF {rpt_id_column} sample: {summary_df[rpt_id_column].head(3).tolist()}")
    
    # Check if ID columns exist in both dataframes
    if geometry_id_column not in gdf.columns:
        logger.warning(f"Geometry ID column '{geometry_id_column}' not found in {feature_type} geometry data")
        logger.warning(f"Available GDF columns: {list(gdf.columns)}")
        return gdf
    
    if rpt_id_column not in summary_df.columns:
        logger.warning(f"RPT ID column '{rpt_id_column}' not found in {feature_type} summary data")
        logger.warning(f"Available summary columns: {list(summary_df.columns)}")
        return gdf
    
    # Merge the dataframes
    try:
        # Normalize IDs (strip/casefold) for robust matching across sources
        def _norm(s):
            return s.astype(str).str.strip().str.upper()

        gdf_ids_norm = set(_norm(gdf[geometry_id_column]))
        summary_ids_norm = set(_norm(summary_df[rpt_id_column]))
        common_ids = gdf_ids_norm.intersection(summary_ids_norm)
        logger.info(f"Common IDs between geometry and summary: {len(common_ids)} out of {len(gdf_ids_norm)} geometry IDs")
        if len(common_ids) > 0:
            logger.info(f"Sample common IDs: {list(common_ids)[:5]}")
        else:
            logger.warning(f"No matching IDs found!")
            logger.warning(f"GDF IDs sample: {list(gdf_ids_norm)[:5]}")
            logger.warning(f"Summary IDs sample: {list(summary_ids_norm)[:5]}")
        
        # Clean up the summary DataFrame column names first to avoid internal conflicts
        original_rpt_id_column = rpt_id_column
        summary_df_cleaned = _clean_column_names(summary_df)
        
        # Update the RPT ID column name if it was cleaned
        if original_rpt_id_column in summary_df.columns:
            # Find what the original RPT ID column was renamed to
            original_col_index = list(summary_df.columns).index(original_rpt_id_column)
            rpt_id_column_cleaned = list(summary_df_cleaned.columns)[original_col_index]
        else:
            rpt_id_column_cleaned = original_rpt_id_column
        
        logger.info(f"RPT ID column: '{original_rpt_id_column}' -> '{rpt_id_column_cleaned}'")
        
        # Check for overlapping column names and handle them
        gdf_cols = set(gdf.columns)
        summary_cols = set(summary_df_cleaned.columns)
        overlapping_cols = gdf_cols.intersection(summary_cols)
        overlapping_cols.discard(geometry_id_column)        # Remove the join column
        overlapping_cols.discard(rpt_id_column_cleaned)     # Remove the cleaned join column
        
        if overlapping_cols:
            logger.info(f"Found overlapping columns: {list(overlapping_cols)} - will use '_geom' and '_rpt' suffixes")
            suffixes = ('_geom', '_rpt')
        else:
            suffixes = ('', '_rpt')
        
        # Prepare normalized join keys on both sides
        gdf['_norm_id'] = _norm(gdf[geometry_id_column])
        summary_df_cleaned['_norm_id'] = _norm(summary_df_cleaned[rpt_id_column_cleaned])

        # Merge using normalized join keys
        merged_gdf = gdf.merge(
            summary_df_cleaned,
            left_on='_norm_id',
            right_on='_norm_id',
            how='left',
            suffixes=suffixes,
        )
        logger.info(f"Successfully merged RPT summary data for {len(merged_gdf)} {feature_type}")
        
        # Remove helper/join columns
        drop_cols = []
        if rpt_id_column_cleaned in merged_gdf.columns:
            drop_cols.append(rpt_id_column_cleaned)
        if '_norm_id' in merged_gdf.columns:
            drop_cols.append('_norm_id')
        if drop_cols:
            merged_gdf = merged_gdf.drop(columns=drop_cols)
            logger.info(f"Removed duplicate ID column '{rpt_id_column_cleaned}' from merged data")
        
        # Log which features got RPT data
        rpt_cols_to_check = summary_df_cleaned.columns.difference([rpt_id_column_cleaned])
        if suffixes[1]:  # If we used suffixes, adjust column names
            rpt_cols_to_check = [col + suffixes[1] if col in overlapping_cols else col for col in rpt_cols_to_check]
        
        existing_rpt_cols = [col for col in rpt_cols_to_check if col in merged_gdf.columns]
        if existing_rpt_cols:
            rpt_data_count = merged_gdf[existing_rpt_cols].notna().any(axis=1).sum()
            logger.info(f"{rpt_data_count} out of {len(merged_gdf)} {feature_type} have RPT summary data")
        
        # Log final column count
        logger.info(f"Final merged GDF has {len(merged_gdf.columns)} columns")
        
        # Clean up column names for better GIS compatibility
        merged_gdf = _clean_column_names(merged_gdf)
        
        return merged_gdf
    except Exception as e:
        logger.error(f"Failed to merge RPT summary data for {feature_type}: {str(e)}")
        return gdf


@time_function
def create_swmm_shapefiles(swmm_data, output_path, output_format="Shapefile", 
                          junctions_summary=None, outfalls_summary=None, links_summary=None):
    """
    Creates shapefiles or geopackages for SWMM junctions, conduits, and outfalls.
    Optionally merges RPT summary data into the attribute tables.

    Parameters:
    - swmm_data: dict of GeoDataFrames from extract_swmm_inp
    - output_path: str, path to save the shapefiles or geopackages
    - output_format: str, "Shapefile" or "GeoPackage"
    - junctions_summary: DataFrame, optional summary data for junctions from RPT extraction
    - outfalls_summary: DataFrame, optional summary data for outfalls from RPT extraction
    - links_summary: DataFrame, optional summary data for links from RPT extraction

    Returns:
    - list of created file paths
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    shapefile_paths = []

    if 'junctions' in swmm_data:
        junctions_gdf = swmm_data['junctions']
        if not junctions_gdf.empty:
            # Direct normalized name-based merge to preserve canonical RPT columns
            jdf = junctions_gdf.copy()
            sdf = junctions_summary.copy() if junctions_summary is not None else None
            if sdf is not None and not sdf.empty:
                jdf['_key'] = jdf['name'].astype(str).str.strip().str.upper()
                sdf['_key'] = sdf['name'].astype(str).str.strip().str.upper() if 'name' in sdf.columns else sdf['node_id'].astype(str).str.strip().str.upper()
                merged_junctions = jdf.merge(sdf, on='_key', how='left')
                # Prefer geometry name, normalize column
                if 'name' not in merged_junctions.columns and 'name_x' in merged_junctions.columns:
                    merged_junctions = merged_junctions.rename(columns={'name_x': 'name'})
                if 'name_y' in merged_junctions.columns:
                    merged_junctions = merged_junctions.drop(columns=['name_y'])
                merged_junctions = merged_junctions.drop(columns=['_key'])
            else:
                merged_junctions = jdf
            enhanced_junctions = apply_junction_schema(merged_junctions)
            shp_path = save_geodataframe(enhanced_junctions, output_path, 'junctions', 
                                       enhanced_junctions.crs.to_epsg(), output_format, logger)
            shapefile_paths.append(shp_path)
        else:
            logger.warning("No junctions data to save.")

    if 'outfalls' in swmm_data:
        outfalls_gdf = swmm_data['outfalls']
        if not outfalls_gdf.empty:
            # Direct normalized name-based merge to preserve canonical RPT columns
            odf = outfalls_gdf.copy()
            sdf = outfalls_summary.copy() if outfalls_summary is not None else None
            if sdf is not None and not sdf.empty:
                odf['_key'] = odf['name'].astype(str).str.strip().str.upper()
                # If summary has canonical 'name', use it; else fall back to 'node_id'
                join_col = 'name' if 'name' in sdf.columns else 'node_id'
                sdf['_key'] = sdf[join_col].astype(str).str.strip().str.upper()
                merged_outfalls = odf.merge(sdf, on='_key', how='left')
                if 'name' not in merged_outfalls.columns and 'name_x' in merged_outfalls.columns:
                    merged_outfalls = merged_outfalls.rename(columns={'name_x': 'name'})
                if 'name_y' in merged_outfalls.columns:
                    merged_outfalls = merged_outfalls.drop(columns=['name_y'])
                merged_outfalls = merged_outfalls.drop(columns=['_key'])
            else:
                merged_outfalls = odf
            enhanced_outfalls = apply_outfall_schema(merged_outfalls)
            shp_path = save_geodataframe(enhanced_outfalls, output_path, 'outfalls',
                                         enhanced_outfalls.crs.to_epsg(), output_format, logger)
            shapefile_paths.append(shp_path)
        else:
            logger.warning("No outfalls data to save.")

    if 'conduits' in swmm_data:
        conduits_gdf = swmm_data['conduits']
        if not conduits_gdf.empty:
            cdf = conduits_gdf.copy()
            ldf = links_summary.copy() if links_summary is not None else None
            if ldf is not None and not ldf.empty:
                cdf['_key'] = cdf['name'].astype(str).str.strip().str.upper()
                ldf['_key'] = (ldf['name'] if 'name' in ldf.columns else ldf['link_id']).astype(str).str.strip().str.upper()
                merged_conduits = cdf.merge(ldf, on='_key', how='left')
                if 'name' not in merged_conduits.columns and 'name_x' in merged_conduits.columns:
                    merged_conduits = merged_conduits.rename(columns={'name_x': 'name'})
                if 'name_y' in merged_conduits.columns:
                    merged_conduits = merged_conduits.drop(columns=['name_y'])
                merged_conduits = merged_conduits.drop(columns=['_key'])
            else:
                merged_conduits = cdf
            enhanced_conduits = apply_link_schema(merged_conduits)
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

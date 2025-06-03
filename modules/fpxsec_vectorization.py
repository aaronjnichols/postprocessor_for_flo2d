"""Module for creating vectorized cross-section data from FLO-2D output."""

import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from typing import Optional, Dict
import logging

from modules.fpxsec_extraction import fpxsec_extract
from modules.hycross_extraction import hycross_extract
from modules.hycross_plots import create_hycross_plots

def create_xsection_geodata(
    fpxsec_file: str,
    hycross_file: str,
    model_data_df: pd.DataFrame,
    coord_system: int,
    output_path: str,
    output_format: str = "gpkg"
) -> Optional[str]:
    """Create vectorized cross section data."""
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    try:
        # Extract data from input files
        fpxsec_df = fpxsec_extract(fpxsec_file)
        if fpxsec_df.empty:
            logger.error("No cross section data extracted from FPXSEC.DAT")
            return None
            
        # Extract hydraulic data if available
        try:
            hycross_summary_df, _ = hycross_extract(hycross_file)
            if not hycross_summary_df.empty:
                fpxsec_df = _merge_xsection_data(fpxsec_df, hycross_summary_df)
        except Exception as e:
            logger.warning(f"Could not process HYCROSS.OUT: {str(e)}")
        
        # Create geometry
        gdf = _create_geometry(fpxsec_df, model_data_df, coord_system)
        if gdf is None:
            return None
            
        # Create output filename with correct extension
        if output_format.lower() in ['gpkg', 'geopackage']:
            extension = 'gpkg'
            driver = 'GPKG'
        else:
            extension = 'shp'
            driver = 'ESRI Shapefile'
            
        # Create output file path
        output_file = os.path.join(output_path, f"fpxsec.{extension}")
        
        # Save to file
        gdf.to_file(output_file, driver=driver)
        logger.info(f"Created cross sections file: {output_file}")
        
        # Create plots and spreadsheets
        excel_path, pdf_path = create_hycross_plots(os.path.dirname(hycross_file))
        if excel_path and pdf_path:
            logger.info("Cross section plots and spreadsheets created successfully")
        
        return output_file
        
    except Exception as e:
        logger.error(f"Failed to process cross sections: {str(e)}")
        return None

def _merge_xsection_data(fpxsec_df: pd.DataFrame, hycross_df: pd.DataFrame) -> pd.DataFrame:
    """Merge FPXSEC.DAT and HYCROSS.OUT data."""
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    try:
        if not hycross_df.empty:
            # Ensure both DataFrames have the 'fpxs_id' column
            if 'fpxs_id' in fpxsec_df.columns and 'fpxs_id' in hycross_df.columns:
                merged_df = pd.merge(
                    fpxsec_df,
                    hycross_df,
                    on='fpxs_id',
                    how='left'
                )
                logger.debug(f"Successfully merged cross section data. Shape: {merged_df.shape}")
            else:
                logger.error("Missing 'fpxs_id' column in one of the DataFrames")
                return fpxsec_df
        else:
            logger.warning("HYCROSS.OUT data is empty, proceeding without merge")
            merged_df = fpxsec_df
            
        return merged_df
        
    except Exception as e:
        logger.error(f"Error merging cross section data: {str(e)}")
        return fpxsec_df

def _create_geometry(
    xsections_df: pd.DataFrame,
    model_data_df: pd.DataFrame,
    coord_system: int
) -> Optional[gpd.GeoDataFrame]:
    """Create geometry for cross sections."""
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    try:
        features = []
        for _, xs in xsections_df.iterrows():
            try:
                # Get start and end cell coordinates from model_data_df
                start_coords = model_data_df[model_data_df['grid_id'] == xs['start_cell']][['x', 'y']].iloc[0]
                end_coords = model_data_df[model_data_df['grid_id'] == xs['end_cell']][['x', 'y']].iloc[0]
                
                # Create line geometry
                line = LineString([
                    (start_coords['x'], start_coords['y']),
                    (end_coords['x'], end_coords['y'])
                ])
                
                # Create feature with base properties
                feature = {
                    'geometry': line,
                    'properties': {
                        'fpxs_id': xs['fpxs_id'],
                        'start_cell': xs['start_cell'],
                        'end_cell': xs['end_cell'],
                        'flow_direction': xs['flow_direction']
                    }
                }
                
                # Add all additional columns from the DataFrame
                for col in xs.index:
                    if col not in ['fpxs_id', 'start_cell', 'end_cell', 'flow_direction']:
                        # Skip any geometry columns
                        if 'geometry' not in col.lower():
                            value = xs[col]
                            # Convert lists to strings
                            if isinstance(value, list):
                                value = ','.join(map(str, value))
                            feature['properties'][col] = value
                        
                features.append(feature)
                logger.debug(f"Created geometry for cross section {xs['fpxs_id']}")
                
            except Exception as e:
                logger.error(f"Failed to create geometry for cross section {xs['fpxs_id']}: {str(e)}")
                continue
        
        if not features:
            logger.warning("No valid geometries created")
            return None
            
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features, crs=f"EPSG:{coord_system}")
        logger.info(f"Created {len(gdf)} cross section geometries")
        
        # Log the columns to verify HYCROSS data is included
        logger.debug(f"GeoDataFrame columns: {list(gdf.columns)}")
        
        return gdf
        
    except Exception as e:
        logger.error(f"Error creating geometry: {str(e)}")
        return None

def _save_output(
    gdf: gpd.GeoDataFrame,
    output_path: str,
    output_format: str,
    coord_system: int
) -> str:
    """Save GeoDataFrame to file."""
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if output_format == "Shapefile":
        output_file = os.path.join(output_path, 'fpxsec.shp')
        driver = "ESRI Shapefile"
    elif output_format == "GeoPackage":
        output_file = os.path.join(output_path, 'fpxsec.gpkg')
        driver = "GPKG"
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    try:
        gdf.to_file(output_file, driver=driver)
        logger.info(f"Cross-sections {output_format} created at: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Failed to create {output_format}: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage
    folder_path = r"R:\_anichols\Projects\_flo2d_postprocessor_tests\Detroit_Basin_Prop100y24h"
    fpxsec_file = os.path.join(folder_path, "FPXSEC.DAT")
    hycross_file = os.path.join(folder_path, "HYCROSS.OUT")
    
    # Assuming model_data_df is available
    output_file = create_xsection_geodata(
        fpxsec_file=fpxsec_file,
        hycross_file=hycross_file,
        model_data_df=model_data_df,  # This needs to be provided
        coord_system=2223,  # Example EPSG code
        output_path=folder_path,
        output_format="Shapefile"
    )
    
    if output_file:
        print(f"Created vectorized cross-sections at: {output_file}")
    else:
        print("No cross-sections were vectorized")
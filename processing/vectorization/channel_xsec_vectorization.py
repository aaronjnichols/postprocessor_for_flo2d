"""Channel cross-section vectorization module.

This module creates line vector files for channel cross-sections using bank relationship
data from CHANBANK.DAT and channel results from CHANMAX.OUT. The resulting vector contains
cross-section lines connecting left and right banks with hydraulic results.
"""

# Standard library imports
import os
import logging

# Third-party imports
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString

# Local application imports
from core.utilities import time_function
from core.constants import GRID_ID, X_COORD, Y_COORD, MAX_DISCHARGE, MAX_STAGE
from extraction.dat.chanbank_dat_extraction import extract_chanbank_dat
from extraction.dat.chan_dat_extraction import extract_chan_dat
from extraction.out.chanmax_out_extraction import extract_chanmax_out
from core.model_data_extraction import extract_model_data_to_df


@time_function
def create_channel_xsec_shapefile(
    file_path: str,
    coord_system: int,
    output_path: str,
    output_format: str = "Shapefile",
) -> str:
    """Create a vector file of channel cross-section lines with hydraulic results.

    Args:
        file_path (str): Path to the FLO-2D project directory.
        coord_system (int): EPSG code for spatial reference.
        output_path (str): Directory to save the output file.
        output_format (str, optional): "Shapefile" or "GeoPackage".
            Defaults to "Shapefile".

    Returns:
        str: Path to the created shapefile or geopackage, or None if creation failed.
    """
    logger = logging.getLogger("FLO2D_Postprocessor")

    try:
        # Extract required data
        logger.info("Extracting channel bank relationships from CHANBANK.DAT")
        chanbank_df = extract_chanbank_dat(file_path)
        
        if chanbank_df.empty:
            logger.warning("No CHANBANK.DAT data found. Skipping cross-section shapefile creation.")
            return None

        logger.info("Extracting channel data from CHAN.DAT")
        chan_data = extract_chan_dat(file_path)
        segments_df = chan_data.get('segments', pd.DataFrame())
        channel_elements_df = chan_data.get('channels', pd.DataFrame())
        
        logger.info("Extracting channel results from CHANMAX.OUT")
        chanmax_df = extract_chanmax_out(file_path)
        
        logger.info("Extracting model coordinates")
        model_data = extract_model_data_to_df(file_path)
        
        if not {GRID_ID, X_COORD, Y_COORD}.issubset(model_data.columns):
            missing = {GRID_ID, X_COORD, Y_COORD} - set(model_data.columns)
            logger.error(f"Model data missing required columns: {missing}")
            return None

        # Create coordinate lookup dictionary
        coord_lookup = model_data.set_index(GRID_ID)[[X_COORD, Y_COORD]].to_dict('index')
        
        # Create channel length lookup from CHAN.DAT
        channel_length_lookup = {}
        if not channel_elements_df.empty:
            channel_length_lookup = channel_elements_df.set_index(GRID_ID)['length'].to_dict()
        
        # Process cross-sections
        features = []
        missing_coords = 0
        
        for _, row in chanbank_df.iterrows():
            xsec_id = row['xsec_id']
            left_bank = row['left_bank']
            right_bank = row['right_bank']
            
            # Get coordinates for left and right banks
            if left_bank in coord_lookup and right_bank in coord_lookup:
                left_coords = (coord_lookup[left_bank][X_COORD], coord_lookup[left_bank][Y_COORD])
                right_coords = (coord_lookup[right_bank][X_COORD], coord_lookup[right_bank][Y_COORD])
                
                # Create LineString geometry
                geometry = LineString([left_coords, right_coords])
                
                # Get hydraulic results if available
                max_discharge = None
                max_stage = None
                time_max_discharge = None
                time_max_stage = None
                
                if not chanmax_df.empty:
                    # Try to match with left bank first, then right bank
                    # CHANMAX nodes are integers, not strings
                    result_row = chanmax_df[chanmax_df['node'] == left_bank]
                    if result_row.empty:
                        result_row = chanmax_df[chanmax_df['node'] == right_bank]
                    
                    if not result_row.empty:
                        max_discharge = result_row.iloc[0]['max_discharge']
                        max_stage = result_row.iloc[0]['max_stage']
                        time_max_discharge = result_row.iloc[0]['time_max_discharge']
                        time_max_stage = result_row.iloc[0]['time_max_stage']
                
                # Get channel length from CHAN.DAT, fallback to geometry length
                channel_length = None
                if left_bank in channel_length_lookup:
                    channel_length = channel_length_lookup[left_bank]
                elif right_bank in channel_length_lookup:
                    channel_length = channel_length_lookup[right_bank]
                else:
                    # Fallback to geometric distance if CHAN.DAT length not available
                    channel_length = geometry.length
                
                # Create feature properties
                properties = {
                    'xsec_id': xsec_id,
                    'left_bank': left_bank,
                    'right_bank': right_bank,
                    'max_q_cfs': max_discharge,
                    'max_stage': max_stage,
                    'time_max_q': time_max_discharge,
                    'time_max_s': time_max_stage,
                    'length_ft': channel_length,
                    'width_ft': geometry.length  # Cross-sectional width
                }
                
                features.append({
                    'geometry': geometry,
                    'properties': properties
                })
            else:
                missing_coords += 1
                
        if missing_coords > 0:
            logger.warning(f"Missing coordinates for {missing_coords} cross-sections")
            
        if not features:
            logger.warning("No valid cross-section features created")
            return None
            
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features, crs=f"EPSG:{coord_system}")
        
        # Determine output file path and format
        if output_format == "GeoPackage":
            output_file = os.path.join(output_path, "channel_xsec_lines.gpkg")
            driver = "GPKG"
        else:
            output_file = os.path.join(output_path, "channel_xsec_lines.shp")
            driver = "ESRI Shapefile"
        
        # Save to file
        gdf.to_file(output_file, driver=driver)
        
        logger.info(f"Created {len(gdf)} channel cross-section features")
        logger.info(f"Channel cross-section lines saved to: {output_file}")
        
        return output_file
        
    except Exception as e:
        logger.error(f"Failed to create channel cross-section shapefile: {e}")
        return None
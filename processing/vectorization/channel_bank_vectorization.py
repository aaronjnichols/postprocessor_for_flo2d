"""Channel bank segment vectorization module.

This module creates line vector files for channel bank segments using channel element
data from CHAN.DAT and bank relationships from CHANBANK.DAT. The resulting vector contains
left and right bank polylines organized by channel segments.
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
from core.constants import GRID_ID, X_COORD, Y_COORD
from extraction.dat.chanbank_dat_extraction import extract_chanbank_dat
from extraction.dat.chan_dat_extraction import extract_chan_dat
from core.model_data_extraction import extract_model_data_to_df


@time_function
def create_channel_bank_shapefile(
    file_path: str,
    coord_system: int,
    output_path: str,
    output_format: str = "Shapefile",
) -> str:
    """Create a vector file of channel bank segment lines with segment attributes.

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
            logger.warning("No CHANBANK.DAT data found. Skipping bank segment shapefile creation.")
            return None

        logger.info("Extracting channel data from CHAN.DAT")
        chan_data = extract_chan_dat(file_path)
        segments_df = chan_data.get('segments', pd.DataFrame())
        elements_df = chan_data.get('channels', pd.DataFrame())
        
        if elements_df.empty:
            logger.warning("No channel elements found. Skipping bank segment shapefile creation.")
            return None
        
        logger.info("Extracting model coordinates")
        model_data = extract_model_data_to_df(file_path)
        
        if not {GRID_ID, X_COORD, Y_COORD}.issubset(model_data.columns):
            missing = {GRID_ID, X_COORD, Y_COORD} - set(model_data.columns)
            logger.error(f"Model data missing required columns: {missing}")
            return None

        # Create coordinate lookup dictionary
        coord_lookup = model_data.set_index(GRID_ID)[[X_COORD, Y_COORD]].to_dict('index')
        
        # Prepare elements with xsec_id assignment
        # Reset index to get file order, then create xsec_id (1-based)
        elements_df = elements_df.reset_index(drop=True)
        elements_df['xsec_id'] = elements_df.index + 1
        
        # Merge channel elements with bank data
        merged_df = pd.merge(elements_df, chanbank_df, on='xsec_id', how='inner')
        
        if merged_df.empty:
            logger.warning("No matching data between channel elements and bank relationships")
            return None
        
        # Create segment lookup from segments data
        # Convert 0-based segment_ids to 1-based for output
        segment_lookup = {}
        if not segments_df.empty:
            for _, row in segments_df.iterrows():
                segment_id_0based = row['segment_id']
                segment_id_1based = segment_id_0based + 1
                segment_lookup[segment_id_0based] = row.to_dict()
                segment_lookup[segment_id_0based]['display_segment_id'] = segment_id_1based
        
        # Process bank segments by segment_id
        features = []
        missing_coords = 0
        
        # Group by segment_id and process each segment
        grouped = merged_df.groupby('segment_id', sort=False)
        
        for segment_id, group in grouped:
            segment_id = int(segment_id)
            
            # Sort by xsec_id to maintain proper flow direction order
            group_sorted = group.sort_values('xsec_id', ascending=True)
            
            # Get segment properties
            segment_props = segment_lookup.get(segment_id, {})
            
            # Create left bank line
            left_coords = []
            for _, row in group_sorted.iterrows():
                left_bank_id = row['left_bank']
                if left_bank_id in coord_lookup:
                    left_coords.append((
                        coord_lookup[left_bank_id][X_COORD],
                        coord_lookup[left_bank_id][Y_COORD]
                    ))
                else:
                    missing_coords += 1
            
            if len(left_coords) >= 2:
                left_geometry = LineString(left_coords)
                left_properties = {
                    'segment_id': segment_props.get('display_segment_id', segment_id + 1),
                    'bank_side': 'left',
                    'length_ft': left_geometry.length,
                    'xsec_count': len(group_sorted)
                }
                
                # Add segment properties with correct field names
                if segment_props:
                    left_properties.update({
                        'initial_de': segment_props.get('depinitial'),
                        'froude_cri': segment_props.get('froudc'),
                        'roughness_': segment_props.get('roughadj'),
                        'sed_transp': segment_props.get('isedn')
                    })
                
                features.append({
                    'geometry': left_geometry,
                    'properties': left_properties
                })
            
            # Create right bank line
            right_coords = []
            for _, row in group_sorted.iterrows():
                right_bank_id = row['right_bank']
                if right_bank_id in coord_lookup:
                    right_coords.append((
                        coord_lookup[right_bank_id][X_COORD],
                        coord_lookup[right_bank_id][Y_COORD]
                    ))
                else:
                    missing_coords += 1
            
            if len(right_coords) >= 2:
                right_geometry = LineString(right_coords)
                right_properties = {
                    'segment_id': segment_props.get('display_segment_id', segment_id + 1),
                    'bank_side': 'right',
                    'length_ft': right_geometry.length,
                    'xsec_count': len(group_sorted)
                }
                
                # Add segment properties with correct field names
                if segment_props:
                    right_properties.update({
                        'initial_de': segment_props.get('depinitial'),
                        'froude_cri': segment_props.get('froudc'),
                        'roughness_': segment_props.get('roughadj'),
                        'sed_transp': segment_props.get('isedn')
                    })
                
                features.append({
                    'geometry': right_geometry,
                    'properties': right_properties
                })
                
        if missing_coords > 0:
            logger.warning(f"Missing coordinates for {missing_coords} bank points")
            
        if not features:
            logger.warning("No valid bank segment features created")
            return None
            
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features, crs=f"EPSG:{coord_system}")
        
        # Determine output file path and format
        if output_format == "GeoPackage":
            output_file = os.path.join(output_path, "channel_bank_segments.gpkg")
            driver = "GPKG"
        else:
            output_file = os.path.join(output_path, "channel_bank_segments.shp")
            driver = "ESRI Shapefile"
        
        # Save to file
        gdf.to_file(output_file, driver=driver)
        
        unique_segments = gdf['segment_id'].nunique()
        logger.info(f"Created {len(gdf)} channel bank features across {unique_segments} segments")
        logger.info(f"Channel bank segments saved to: {output_file}")
        
        return output_file
        
    except Exception as e:
        logger.error(f"Failed to create channel bank shapefile: {e}")
        return None
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import os
from modules.swmm_inp_rpt_node_extraction import extract_node_data
from modules.swmm_inp_rpt_link_extraction import extract_link_data

def create_swmm_geodata(folder_path: str, epsg: int, output_format: str = 'gpkg') -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Create spatial data from SWMM nodes and links, joining coordinate data and creating geodataframes.
    
    Args:
        folder_path (str): Path to folder containing SWMM files
        epsg (int): EPSG code for the coordinate reference system
        output_format (str): Output format - 'gpkg', 'shp', 'Shapefile', or 'GeoPackage'
        
    Returns:
        tuple: (nodes_gdf, links_gdf) - GeoDataFrames for nodes and links
        
    Raises:
        ValueError: If output_format is not one of the accepted values
    """
    # Validate and standardize output format
    format_mapping = {
        'gpkg': 'GPKG',
        'geopackage': 'GPKG',
        'shp': 'ESRI Shapefile',
        'shapefile': 'ESRI Shapefile'
    }
    
    output_format = output_format.lower()
    if output_format not in format_mapping:
        raise ValueError("Output format must be one of: 'gpkg', 'shp', 'Shapefile', or 'GeoPackage'")
    
    driver = format_mapping[output_format]
    extension = '.gpkg' if driver == 'GPKG' else '.shp'

    # Extract nodes and links data
    nodes_df = extract_node_data(folder_path)
    links_df = extract_link_data(folder_path)
    
    # Add debugging prints
    print(f"Number of nodes extracted: {len(nodes_df)}") # debug print
    print(f"Number of links extracted: {len(links_df)}") # debug print
    
    # Debug column names
    print("\nNode DataFrame columns:") # debug print
    print(nodes_df.columns) # debug print
    
    # Verify node coordinates using correct column names
    print("\nFirst few node coordinates:") # debug print
    print(nodes_df[['node_id', 'X_Coord', 'Y_Coord']].head()) # debug print
    
    # Create nodes geodataframe using correct column names
    geometry = [Point(xy) for xy in zip(nodes_df['X_Coord'], nodes_df['Y_Coord'])]
    nodes_gdf = gpd.GeoDataFrame(nodes_df, geometry=geometry, crs=f"EPSG:{epsg}")
    
    # Debug the link joining process
    print("\nFirst few links before joining:") # debug print
    print(links_df[['link_id', 'from_node', 'to_node']].head()) # debug print
    
    # Join coordinates to links dataframe using correct column names
    links_with_coords = (
        links_df
        .merge(
            nodes_df[['node_id', 'X_Coord', 'Y_Coord']], 
            left_on='from_node', 
            right_on='node_id',
            how='left',
            suffixes=('', '_from')
        )
        .merge(
            nodes_df[['node_id', 'X_Coord', 'Y_Coord']], 
            left_on='to_node', 
            right_on='node_id',
            how='left',
            suffixes=('_from', '_to')
        )
        .drop(['node_id_from', 'node_id_to'], axis=1)
    )
    
    # Debug the joining results
    print(f"\nNumber of links after joining: {len(links_with_coords)}") # debug print
    print("\nFirst few links with coordinates:") # debug print
    print(links_with_coords[['link_id', 'from_node', 'to_node', 
                            'X_Coord_from', 'Y_Coord_from', 
                            'X_Coord_to', 'Y_Coord_to']].head()) # debug print
    
    # Check for any missing coordinates
    missing_coords = links_with_coords[
        links_with_coords[['X_Coord_from', 'Y_Coord_from', 
                          'X_Coord_to', 'Y_Coord_to']].isna().any(axis=1)
    ]
    if not missing_coords.empty:
        print("\nWarning: Some links have missing coordinates:") # debug print
        print(missing_coords[['link_id', 'from_node', 'to_node']]) # debug print

    # Create LineString geometries for links using correct column names
    geometry = [
        LineString([(row['X_Coord_from'], row['Y_Coord_from']), 
                   (row['X_Coord_to'], row['Y_Coord_to'])])
        for _, row in links_with_coords.iterrows()
    ]
    
    # Create links geodataframe
    links_gdf = gpd.GeoDataFrame(links_with_coords, geometry=geometry, crs=f"EPSG:{epsg}")

    # Create output folder if it doesn't exist
    output_folder = os.path.join(folder_path, 'flo2d_shp')
    os.makedirs(output_folder, exist_ok=True)

    # Export based on specified format
    nodes_gdf.to_file(os.path.join(output_folder, f'swmm_nodes{extension}'), driver=driver)
    links_gdf.to_file(os.path.join(output_folder, f'swmm_links{extension}'), driver=driver)

    return nodes_gdf, links_gdf

if __name__ == "__main__":
    # Example usage
    folder_path = r"R:\_anichols\Projects\_flo2d_postprocessor_tests\Detroit_Basin_Prop100y24h"
    nodes_gdf, links_gdf = create_swmm_geodata(folder_path, epsg=2868, output_format='gpkg')
    
    # Print first few rows of each geodataframe
    print("\nNodes GeoDataFrame head:") # debug print
    print(nodes_gdf.head()) # debug print
    
    print("\nLinks GeoDataFrame head:") # debug print
    print(links_gdf.head()) # debug print
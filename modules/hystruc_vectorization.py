# hystruc_vectorization.py

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import os
from typing import Optional
from modules.hystruc_extraction import hystruc_extract
from modules.hydrostruct_extraction import hydrostruct_extract
import logging

def create_structure_geodata(
    dat_file: str,
    out_file: str,
    model_data_df: pd.DataFrame,
    coord_system: int,
    output_path: str,
    output_format: str = "Shapefile"
) -> Optional[str]:
    """
    Create a vectorized representation of hydraulic structures with combined DAT and OUT data.
    
    Args:
        dat_file: Path to HYSTRUC.DAT file
        out_file: Path to HYDROSTRUCT.OUT file
        model_data_df: DataFrame with grid cell information (grid_id, x, y)
        coord_system: EPSG code for coordinate system
        output_path: Directory to save output file
        output_format: "Shapefile" or "GeoPackage"
        
    Returns:
        Path to created file or None if no structures to process
    """
    # Read DAT and OUT files
    dat_data = hystruc_extract(dat_file)
    out_info, out_timeseries = hydrostruct_extract(out_file)
    
    # Merge structure data from both sources
    structures_df = _merge_structure_data(dat_data['structures'], out_info)
    
    # Create vectorized structures
    gdf = _create_geometry(structures_df, model_data_df, coord_system)
    
    if gdf is None or gdf.empty:
        return None
        
    return _save_output(gdf, output_path, output_format, coord_system)

def _merge_structure_data(dat_df: pd.DataFrame, out_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge structure data from DAT and OUT files.
    
    Args:
        dat_df: DataFrame from HYSTRUC.DAT
        out_df: DataFrame from HYDROSTRUCT.OUT
        
    Returns:
        Merged DataFrame with combined structure information
    """
    # Merge on structure name
    merged_df = pd.merge(
        dat_df,
        out_df,
        left_on='name',
        right_on='name',
        how='outer',
        suffixes=('_dat', '_out')
    )
    
    # Log any structures that don't match between files
    _log_unmatched_structures(merged_df)
    
    return merged_df

def _log_unmatched_structures(merged_df: pd.DataFrame) -> None:
    """Log structures that don't have matches in both files."""
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    # Identify structures only in DAT file
    dat_only = merged_df[merged_df['max_discharge'].isna()]['name'].tolist()
    if dat_only:
        logger.warning(f"Structures in DAT file but not in OUT file: {dat_only}")
    
    # Identify structures only in OUT file
    out_only = merged_df[merged_df['type'].isna()]['name'].tolist()
    if out_only:
        logger.warning(f"Structures in OUT file but not in DAT file: {out_only}")

def _create_geometry(
    structures_df: pd.DataFrame,
    model_data_df: pd.DataFrame,
    coord_system: int
) -> Optional[gpd.GeoDataFrame]:
    """
    Create geometry for structures using inflow/outflow nodes.
    
    Args:
        structures_df: Merged structure data
        model_data_df: Grid cell data with coordinates
        coord_system: EPSG code
        
    Returns:
        GeoDataFrame with structure geometries or None if no valid structures
    """
    # Merge with model data to get coordinates
    merged_df = pd.merge(
        structures_df,
        model_data_df[['grid_id', 'x', 'y']],
        left_on='inflow_node',
        right_on='grid_id',
        how='left'
    )
    merged_df.rename(columns={'x': 'inflow_x', 'y': 'inflow_y'}, inplace=True)
    
    merged_df = pd.merge(
        merged_df,
        model_data_df[['grid_id', 'x', 'y']],
        left_on='outflow_node',
        right_on='grid_id',
        how='left',
        suffixes=('', '_outflow')
    )
    merged_df.rename(columns={'x': 'outflow_x', 'y': 'outflow_y'}, inplace=True)
    
    # Create geometries
    geometry = [
        LineString([
            (row['inflow_x'], row['inflow_y']),
            (row['outflow_x'], row['outflow_y'])
        ]) for idx, row in merged_df.iterrows()
        if not pd.isna(row['inflow_x']) and not pd.isna(row['outflow_x'])
    ]
    
    if not geometry:
        return None
        
    return gpd.GeoDataFrame(
        merged_df,
        geometry=geometry,
        crs=f"EPSG:{coord_system}"
    )

def _save_output(
    gdf: gpd.GeoDataFrame,
    output_path: str,
    output_format: str,
    coord_system: int
) -> str:
    """Save GeoDataFrame to file."""
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if output_format == "Shapefile":
        output_file = os.path.join(output_path, 'hydraulic_structures.shp')
        driver = "ESRI Shapefile"
    elif output_format == "GeoPackage":
        output_file = os.path.join(output_path, 'hydraulic_structures.gpkg')
        driver = "GPKG"
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    try:
        gdf.to_file(output_file, driver=driver)
        logger.info(f"Hydraulic Structures {output_format} created at: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Failed to create {output_format}: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage
    folder_path = r"R:\_anichols\Projects\AZ_7_RANCHES\FLO2D\20231212_Added_FPXSEC"
    dat_file = os.path.join(folder_path, "HYSTRUC.DAT")
    out_file = os.path.join(folder_path, "HYDROSTRUCT.OUT")
    
    # Assuming model_data_df is available
    output_file = create_structure_geodata(
        dat_file=dat_file,
        out_file=out_file,
        model_data_df=model_data_df,  # This needs to be provided
        coord_system=2223,  # Example EPSG code
        output_path=folder_path,
        output_format="Shapefile"
    )
    
    if output_file:
        print(f"Created vectorized structures at: {output_file}")
    else:
        print("No structures were vectorized")

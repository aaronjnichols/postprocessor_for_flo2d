#!/usr/bin/env python3
"""
Debug script to test RPT data integration with SWMM shapefiles
"""

import os
import sys
import pandas as pd
import logging

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extraction.dat.swmm_inp_extraction import extract_swmm_inp
from extraction.out.swmmnodes_rpt import extract_swmmnodes_rpt
from extraction.out.swmmlinks_rpt import extract_swmmlinks_rpt
from processing.vectorization.swmm_vectorization import create_swmm_shapefiles

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_rpt_merge(model_folder):
    """Debug RPT data merging process"""
    
    print("=== DEBUGGING RPT DATA INTEGRATION ===")
    
    # 1. Extract SWMM geometry data
    print("\n1. Extracting SWMM geometry data...")
    swmm_inp_file = os.path.join(model_folder, 'SWMM.INP')
    if not os.path.exists(swmm_inp_file):
        print(f"ERROR: SWMM.INP not found at {swmm_inp_file}")
        return
    
    swmm_data = extract_swmm_inp(swmm_inp_file, 2898)
    
    print("SWMM Geometry Data:")
    for key, gdf in swmm_data.items():
        if not gdf.empty:
            print(f"  {key}: {len(gdf)} features")
            print(f"    Columns: {list(gdf.columns)}")
            if 'node_id' in gdf.columns:
                print(f"    Sample node_ids: {gdf['node_id'].head(3).tolist()}")
            elif 'link_id' in gdf.columns:
                print(f"    Sample link_ids: {gdf['link_id'].head(3).tolist()}")
    
    # 2. Extract RPT data
    print("\n2. Extracting RPT data...")
    rpt_file = None
    for filename in os.listdir(model_folder):
        if filename.lower().endswith('.rpt'):
            rpt_file = os.path.join(model_folder, filename)
            break
    
    if not rpt_file:
        print("ERROR: No .rpt file found")
        return
    
    print(f"Found RPT file: {rpt_file}")
    
    # Extract nodes data
    nodes_data = extract_swmmnodes_rpt(model_folder)
    full_nodes_summary = nodes_data.get('merged_results', pd.DataFrame())
    
    print(f"\nNodes RPT Data:")
    print(f"  Shape: {full_nodes_summary.shape}")
    print(f"  Columns: {list(full_nodes_summary.columns)}")
    if not full_nodes_summary.empty:
        print(f"  Node types: {full_nodes_summary['type'].unique()}")
        print(f"  Sample node_ids: {full_nodes_summary['node_id'].head(3).tolist()}")
    
    # Separate junctions and outfalls
    junctions_summary = None
    outfalls_summary = None
    if not full_nodes_summary.empty:
        junctions_summary = full_nodes_summary[full_nodes_summary['type'] == 'JUNCTION'].copy()
        outfalls_summary = full_nodes_summary[full_nodes_summary['type'] == 'OUTFALL'].copy()
        print(f"  Junctions: {len(junctions_summary)}")
        print(f"  Outfalls: {len(outfalls_summary)}")
    
    # Extract links data
    links_data = extract_swmmlinks_rpt(model_folder)
    links_summary = links_data.get('merged_results', pd.DataFrame())
    
    print(f"\nLinks RPT Data:")
    print(f"  Shape: {links_summary.shape}")
    print(f"  Columns: {list(links_summary.columns)}")
    if not links_summary.empty:
        print(f"  Sample link_ids: {links_summary['link_id'].head(3).tolist()}")
    
    # 3. Test the merge process
    print("\n3. Testing merge process...")
    
    output_path = os.path.join(model_folder, "debug_shapefiles")
    os.makedirs(output_path, exist_ok=True)
    
    try:
        created_files = create_swmm_shapefiles(
            swmm_data, 
            output_path, 
            output_format="Shapefile",
            junctions_summary=junctions_summary,
            outfalls_summary=outfalls_summary,
            links_summary=links_summary
        )
        
        print(f"\nCreated files: {created_files}")
        
        # Check the actual output files
        print("\n4. Checking output files...")
        for file_path in created_files:
            if os.path.exists(file_path):
                # Read the shapefile to check columns
                import geopandas as gpd
                gdf = gpd.read_file(file_path)
                print(f"\nFile: {os.path.basename(file_path)}")
                print(f"  Shape: {gdf.shape}")
                print(f"  Columns: {list(gdf.columns)}")
                
                # Look for RPT columns (anything that's not basic geometry columns)
                basic_cols = ['geometry', 'node_id', 'link_id', 'x_coord', 'y_coord', 'inv_elev', 'max_depth', 'pond_area', 'type']
                rpt_cols = [col for col in gdf.columns if col not in basic_cols]
                if rpt_cols:
                    print(f"  RPT columns found: {rpt_cols}")
                    # Check if any RPT data exists
                    for col in rpt_cols[:3]:  # Check first 3 RPT columns
                        non_null_count = gdf[col].notna().sum()
                        print(f"    {col}: {non_null_count} non-null values")
                else:
                    print(f"  NO RPT columns found!")
            else:
                print(f"File not created: {file_path}")
                
    except Exception as e:
        print(f"ERROR during merge: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_rpt_merge.py <model_folder>")
        sys.exit(1)
    
    model_folder = sys.argv[1]
    debug_rpt_merge(model_folder)
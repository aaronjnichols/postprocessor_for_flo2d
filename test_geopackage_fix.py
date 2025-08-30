#!/usr/bin/env python3
"""
Test script to specifically test the GeoPackage field error fix
"""

import os
import sys
import logging
import pytest
import pandas as pd

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extraction.dat.swmm_inp_extraction import extract_swmm_inp
from extraction.out.swmm_junctions_rpt import extract_swmm_junctions_rpt
from extraction.out.swmm_outfalls_rpt import extract_swmm_outfalls_rpt
from processing.vectorization.swmm_vectorization import create_swmm_shapefiles

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')


@pytest.mark.skip(reason="requires model folder fixture")
def test_geopackage_fix(model_folder):
    """Test if the GeoPackage field error is fixed"""
    
    print("=== TESTING GEOPACKAGE FIELD ERROR FIX ===")
    
    # Extract SWMM geometry data
    swmm_inp_file = os.path.join(model_folder, 'SWMM.INP')
    swmm_data = extract_swmm_inp(swmm_inp_file, 2898)
    
    # Extract RPT data
    junctions_data = extract_swmm_junctions_rpt(model_folder)
    junctions_summary = junctions_data.get('merged_results', pd.DataFrame())
    outfalls_data = extract_swmm_outfalls_rpt(model_folder)
    outfalls_summary = outfalls_data.get('merged_results', pd.DataFrame())
    
    # Extract links data
    from extraction.out.swmmlinks_rpt import extract_swmmlinks_rpt
    links_data = extract_swmmlinks_rpt(model_folder)
    links_summary = links_data.get('merged_results', pd.DataFrame())
    
    # Test GeoPackage creation
    output_path = os.path.join(model_folder, "test_geopackage_fix")
    os.makedirs(output_path, exist_ok=True)
    
    try:
        created_files = create_swmm_shapefiles(
            swmm_data, 
            output_path, 
            output_format="GeoPackage",
            junctions_summary=junctions_summary,
            outfalls_summary=outfalls_summary,
            links_summary=links_summary
        )
        
        print(f"\n✅ SUCCESS: GeoPackage files created without field errors!")
        print(f"Created files: {created_files}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: GeoPackage creation failed with error:")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import pandas as pd
    if len(sys.argv) != 2:
        print("Usage: python test_geopackage_fix.py <model_folder>")
        sys.exit(1)
    
    model_folder = sys.argv[1]
    success = test_geopackage_fix(model_folder)
    sys.exit(0 if success else 1)

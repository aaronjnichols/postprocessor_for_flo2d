#!/usr/bin/env python3
"""
Test script to verify the hydraulic structures fix.
This script tests the specific issue with structure_id column naming.
"""

import os
import sys
import pandas as pd

# Add the modules directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from extraction.dat.hystruc_dat_extraction import extract_hystruc_results
from modules.hydrostruct_out_extraction import extract_hydrostruct_peaks
from core.constants import STRUCTURE_ID

def test_hystruc_fix():
    """Test the hydraulic structures extraction and peak data merging."""
    
    # Test folder path
    test_folder = "K:/24008320 - Sunderban Properties/Project Documents/Reports/Drainage/Models/FLO2D/100Y24H/_D11"
    
    if not os.path.exists(test_folder):
        print(f"Test folder not found: {test_folder}")
        return False
    
    # Check if required files exist
    hystruc_file = os.path.join(test_folder, 'HYSTRUC.DAT')
    hydrostruct_out_file = os.path.join(test_folder, 'HYDROSTRUCT.OUT')
    
    if not os.path.exists(hystruc_file):
        print(f"HYSTRUC.DAT not found: {hystruc_file}")
        return False
    
    print("Testing hydraulic structures extraction...")
    
    try:
        # Test extraction
        hystruc_df, rating_curves = extract_hystruc_results(test_folder)
        print(f"✓ Successfully extracted {len(hystruc_df)} hydraulic structures")
        print(f"✓ Extracted {len(rating_curves)} rating curves")
        
        # Check if the STRUCTURE_ID column exists
        if STRUCTURE_ID in hystruc_df.columns:
            print(f"✓ {STRUCTURE_ID} column found in hydraulic structures DataFrame")
            print(f"  Structure IDs: {list(hystruc_df[STRUCTURE_ID])}")
        else:
            print(f"✗ {STRUCTURE_ID} column NOT found in hydraulic structures DataFrame")
            print(f"  Available columns: {list(hystruc_df.columns)}")
            return False
        
        # Test peak data extraction if file exists
        if os.path.exists(hydrostruct_out_file):
            print("\nTesting peak data extraction...")
            peaks_df = extract_hydrostruct_peaks(test_folder)
            print(f"✓ Successfully extracted peak data for {len(peaks_df)} structures")
            
            if STRUCTURE_ID in peaks_df.columns:
                print(f"✓ {STRUCTURE_ID} column found in peaks DataFrame")
                print(f"  Peak structure IDs: {list(peaks_df[STRUCTURE_ID])}")
            else:
                print(f"✗ {STRUCTURE_ID} column NOT found in peaks DataFrame")
                print(f"  Available columns: {list(peaks_df.columns)}")
                return False
            
            # Test merging
            print("\nTesting merge operation...")
            merged_df = pd.merge(hystruc_df, peaks_df, on=STRUCTURE_ID, how='left')
            print(f"✓ Successfully merged DataFrames. Final shape: {merged_df.shape}")
            
            # Check for successful merge
            if 'qpeak_cfs' in merged_df.columns and 'tpeak_hrs' in merged_df.columns:
                print("✓ Peak data columns found in merged DataFrame")
                return True
            else:
                print("✗ Peak data columns not found in merged DataFrame")
                return False
        else:
            print(f"HYDROSTRUCT.OUT not found: {hydrostruct_out_file}")
            print("✓ Basic hydraulic structures extraction test passed")
            return True
            
    except Exception as e:
        print(f"✗ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Hydraulic Structures Fix")
    print("=" * 40)
    
    success = test_hystruc_fix()
    
    if success:
        print("\n✓ All tests passed! The structure_id fix is working correctly.")
    else:
        print("\n✗ Tests failed. The fix needs more work.")
    
    print("=" * 40) 
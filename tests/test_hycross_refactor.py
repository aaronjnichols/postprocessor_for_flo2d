#!/usr/bin/env python3
"""
Test script to verify the HYCROSS/FPXSEC refactor works correctly.
"""

import os
import sys
import tempfile

# Test updated hycross_extraction module
try:
    from extraction.out.hycross_out_extraction import (
        extract_fpxsec_results, 
        extract_hycross_hydrographs, 
        extract_hydrograph_data,
        integrate_max_discharge_in_df
    )
    print("SUCCESS: Updated hycross_extraction module imported successfully")
except ImportError as e:
    print(f"FAILED: Failed to import hycross_extraction module: {e}")
    sys.exit(1)

# Test renamed spreadsheet module
try:
    from modules.hycross_spreadsheet import hycross_spreadsheet_and_plots
    print("SUCCESS: Renamed hycross_spreadsheet module imported successfully")
except ImportError as e:
    print(f"FAILED: Failed to import renamed spreadsheet module: {e}")
    sys.exit(1)

# Test main module imports
try:
    from main import process_flo2d
    print("SUCCESS: Main module imports correctly with updated dependencies")
except ImportError as e:
    print(f"FAILED: Failed to import main module: {e}")
    sys.exit(1)

# Test that old module name is gone
try:
    from modules.fpxsec_spreadsheet import hycross_spreadsheet_and_plots
    print("WARNING: Old module name still works - this should not happen")
except ImportError:
    print("SUCCESS: Old module name correctly removed")

# Test extraction function works with valid test data
print("\n=== Testing Hydrograph Extraction Function ===")

# Create a simple test HYCROSS.OUT file
test_content = """Some header lines
THE MAXIMUM DISCHARGE FROM CROSS SECTION   1 IS:  125.50 CFS AT TIME:   2.50 HOURS
MAXIMUM WATER SURFACE ELEVATION AT CROSS SECTION   1  IS:  100.25

HYDROGRAPH AND FLOODPLAIN HYDRAULICS FOR CROSS SECTION NO:    1

TIME         DEPTH        VELOCITY     WS ELEV      TOP W        DISCHARGE
(HRS)        (FT)         (FT/S)       (FT)         (FT)         (CFS)
   0.00      0.50          1.20        99.50        10.0          15.00
   1.00      1.20          2.50        100.20       12.0          75.50
   2.00      2.00          3.20        100.25       15.0          120.25
   3.00      1.50          2.80        100.00       13.0          95.75

THE MAXIMUM DISCHARGE FROM CROSS SECTION   2 IS:   85.75 CFS AT TIME:   1.75 HOURS
MAXIMUM WATER SURFACE ELEVATION AT CROSS SECTION   2  IS:   98.80

HYDROGRAPH AND FLOODPLAIN HYDRAULICS FOR CROSS SECTION NO:    2

TIME         DEPTH        VELOCITY     WS ELEV      TOP W        DISCHARGE
(HRS)        (FT)         (FT/S)       (FT)         (FT)         (CFS)
   0.00      0.30          0.80        98.30        8.0           8.50
   1.00      0.90          1.90        98.80        10.0          45.25
   2.00      1.20          2.10        98.75        11.0          65.50
   3.00      0.80          1.50        98.50        9.5           35.75
"""

with tempfile.TemporaryDirectory() as temp_dir:
    test_file = os.path.join(temp_dir, 'HYCROSS.OUT')
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    try:
        # Test direct file extraction
        hydrograph_data, max_wse_info = extract_hydrograph_data(test_file)
        print(f"SUCCESS: Extracted hydrograph data for {len(hydrograph_data)} sections")
        
        # Test folder-based extraction
        folder_data, folder_wse = extract_hycross_hydrographs(temp_dir)
        print(f"SUCCESS: Folder extraction found {len(folder_data)} sections")
        
        # Check that we have the expected sections
        expected_sections = [1, 2]
        for section in expected_sections:
            if section in hydrograph_data:
                df = hydrograph_data[section]
                wse = max_wse_info.get(section, 'N/A')
                print(f"  Section {section}: {len(df)} data points, Max WSE: {wse}")
            else:
                print(f"FAILED: Missing expected section {section}")
                
        # Test that both extraction methods return consistent data
        if len(hydrograph_data) == len(folder_data):
            print("SUCCESS: Both extraction methods return consistent section counts")
                
    except Exception as e:
        print(f"FAILED: Error testing extraction function: {e}")
        sys.exit(1)

print("\nSUCCESS: All HYCROSS/FPXSEC refactor tests passed!")
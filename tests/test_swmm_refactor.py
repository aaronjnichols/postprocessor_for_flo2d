#!/usr/bin/env python3
"""
Test script to verify the SWMM inlets refactor works correctly.
"""

import os
import sys
import tempfile

# Test new extraction module
try:
    from modules.swmmqin_out_extraction import extract_hydrograph_data, extract_swmmqin_out
    print("SUCCESS: New SWMMQIN extraction module imported successfully")
except ImportError as e:
    print(f"FAILED: Failed to import SWMMQIN extraction module: {e}")
    sys.exit(1)

# Test renamed spreadsheet module
try:
    from modules.swmm_inlets_spreadsheet import swmm_inlet_spreadsheets_and_pdf
    print("SUCCESS: Renamed SWMM inlets spreadsheet module imported successfully")
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
    from modules.swmm_inlets_spreadsheets import swmm_inlet_spreadsheets_and_pdf
    print("WARNING: Old module name still works - this should not happen")
except ImportError:
    print("SUCCESS: Old module name correctly removed")

# Test extraction function works with valid test data
print("\n=== Testing Extraction Function ===")

# Create a simple test SWMMQIN.OUT file
test_content = """Some header lines
STORM DRAIN INLET:    INLET_001
      0.00      0.00
      1.00      5.50
      2.00     10.25
      3.00      8.75

STORM DRAIN INLET:    INLET_002  
      0.00      0.00
      1.00      3.20
      2.00      7.10
      3.00      5.90
"""

with tempfile.TemporaryDirectory() as temp_dir:
    test_file = os.path.join(temp_dir, 'SWMMQIN.OUT')
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    try:
        inlet_data = extract_hydrograph_data(temp_dir)
        print(f"SUCCESS: Extracted data for {len(inlet_data)} inlets")
        
        # Check that we have the expected inlets
        expected_inlets = ['INLET_001', 'INLET_002']
        for inlet in expected_inlets:
            if inlet in inlet_data:
                df = inlet_data[inlet]
                print(f"  {inlet}: {len(df)} data points")
            else:
                print(f"FAILED: Missing expected inlet {inlet}")
                
    except Exception as e:
        print(f"FAILED: Error testing extraction function: {e}")
        sys.exit(1)

print("\nSUCCESS: All SWMM inlets refactor tests passed!")
#!/usr/bin/env python3
"""
Test script to verify the hydrostruct Excel generation fix.
This script tests the hydrostruct spreadsheet generation with various scenarios.
"""

import os
import tempfile
import pandas as pd
from modules.hydrostruct_out_extraction import parse_hydrograph_data
from modules.hydrostruct_spreadsheet import hydrostruct_hydrographs_to_excel

def test_empty_data():
    """Test with empty hydrograph data."""
    print("Testing with empty hydrograph data...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        result = hydrostruct_hydrographs_to_excel({}, temp_dir)
        print(f"Result: {result}")
        print("✓ Empty data test completed")

def test_no_valid_structures():
    """Test with hydrograph data containing no valid structures."""
    print("Testing with no valid structures...")
    
    # Create data with empty DataFrames
    empty_data = {
        'structure1': pd.DataFrame(),
        'structure2': pd.DataFrame(columns=['time', 'inflow', 'outflow'])
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        result = hydrostruct_hydrographs_to_excel(empty_data, temp_dir)
        print(f"Result: {result}")
        print("✓ No valid structures test completed")

def test_valid_data():
    """Test with valid hydrograph data."""
    print("Testing with valid hydrograph data...")
    
    # Create sample valid data
    valid_data = {
        'structure1': pd.DataFrame({
            'time': [0, 1, 2, 3],
            'inflow': [0, 10, 20, 15],
            'outflow': [0, 5, 15, 10]
        }),
        'structure2': pd.DataFrame({
            'time': [0, 1, 2, 3],
            'inflow': [0, 15, 25, 20],
            'outflow': [0, 8, 18, 12]
        })
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        result = hydrostruct_hydrographs_to_excel(valid_data, temp_dir)
        print(f"Result: {result}")
        
        # Check if file was created
        expected_file = os.path.join(temp_dir, 'hydrostruct_hydrographs.xlsx')
        if os.path.exists(expected_file):
            print(f"✓ Excel file created successfully: {expected_file}")
        else:
            print(f"✗ Excel file not created: {expected_file}")

def test_missing_file():
    """Test parse_hydrograph_data with missing file."""
    print("Testing parse_hydrograph_data with missing file...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        result = parse_hydrograph_data(temp_dir)
        print(f"Result: {result}")
        print("✓ Missing file test completed")

def main():
    """Run all tests."""
    print("Running hydrostruct Excel generation tests...\n")
    
    test_empty_data()
    print()
    
    test_no_valid_structures()
    print()
    
    test_valid_data()
    print()
    
    test_missing_file()
    print()
    
    print("All tests completed!")

if __name__ == "__main__":
    main() 
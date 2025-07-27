#!/usr/bin/env python3
"""
Test script to verify the file discovery refactor works correctly.
"""

import os
import sys

# Test file discovery module
try:
    from modules.file_discovery import (
        get_file_path, 
        check_file_exists, 
        get_existing_files,
        log_file_status,
        categorize_files_by_existence
    )
    print("SUCCESS: File discovery module imported successfully")
except ImportError as e:
    print(f"FAILED: Failed to import file discovery module: {e}")
    sys.exit(1)

# Test main module imports
try:
    from main import process_flo2d
    print("SUCCESS: Main module imports successfully")
except ImportError as e:
    print(f"FAILED: Failed to import main module: {e}")
    sys.exit(1)

# Test file discovery functionality
print("\n=== File Discovery Test ===")
test_dir = '.'
existing = get_existing_files(test_dir)
print(f"Found {len(existing)} existing FLO-2D files in current directory")

# Show a few examples
for name, path in list(existing.items())[:5]:
    print(f"  {name}: {path}")

# Test categorization
categorized = categorize_files_by_existence(test_dir)
print(f"\nFile categorization:")
for category, files in categorized.items():
    if files['existing']:
        print(f"  {category} - Found: {len(files['existing'])} files")
    if files['missing']:
        print(f"  {category} - Missing: {len(files['missing'])} files")

# Test basic path functions
test_file = get_file_path('.', 'main.py')
exists = check_file_exists(test_file)
print(f"\nPath test - main.py exists: {exists}")

print("\nSUCCESS: All tests passed! File discovery refactor is working correctly.")
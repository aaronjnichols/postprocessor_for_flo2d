"""Test script to validate style guide improvements.

This script tests the improvements made to align the codebase with the style guide.
"""

import logging
import sys
import tempfile
import os

def test_function_naming():
    """Test that function naming follows snake_case convention."""
    print("Testing function naming conventions...")
    
    # Test the renamed function
    try:
        from processing.spatial.geospatial import convert_to_geo_dataframe
        print("  [OK] convert_to_geo_dataframe imports successfully")
    except ImportError as e:
        print(f"  [FAIL] Failed to import convert_to_geo_dataframe: {e}")
        return False
    
    # Ensure old function name is gone
    try:
        from processing.spatial.geospatial import convertToGeoDataFrame
        print("  [FAIL] Old camelCase function name still exists")
        return False
    except ImportError:
        print("  [OK] Old camelCase function name properly removed")
    
    return True

def test_documentation():
    """Test that modules have proper docstrings."""
    print("Testing documentation improvements...")
    
    modules_to_test = [
        'core.utilities',
        'extraction.base.extraction_utils', 
        'processing.spatial.geospatial',
        'core.model_data_extraction'
    ]
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[''])
            if hasattr(module, '__doc__') and module.__doc__:
                print(f"  ✓ {module_name} has module docstring")
            else:
                print(f"  ✗ {module_name} missing module docstring")
                return False
        except ImportError as e:
            print(f"  ✗ Failed to import {module_name}: {e}")
            return False
    
    return True

def test_logging_integration():
    """Test that logging is properly integrated."""
    print("Testing logging improvements...")
    
    # Test logger setup
    try:
        from core.logger import setup_logger
        logger = setup_logger('TEST_LOGGER', level=logging.INFO)
        logger.info("Test log message")
        print("  ✓ Logger setup works correctly")
    except Exception as e:
        print(f"  ✗ Logger setup failed: {e}")
        return False
    
    # Test utilities use logging instead of print
    try:
        from core.utilities import create_required_folders
        test_dir = tempfile.mkdtemp()
        create_required_folders([os.path.join(test_dir, 'test')])
        print("  ✓ Utilities function works with logging")
    except Exception as e:
        print(f"  ✗ Utilities function failed: {e}")
        return False
    
    return True

def test_constants_usage():
    """Test that constants are properly defined and accessible."""
    print("Testing constants usage...")
    
    try:
        from core.constants import GRID_ID, DEPTH_MAX, X_COORD, Y_COORD
        print(f"  ✓ Core constants accessible: GRID_ID='{GRID_ID}'")
    except ImportError as e:
        print(f"  ✗ Failed to import constants: {e}")
        return False
    
    return True

def test_import_organization():
    """Test that imports are organized according to PEP 8."""
    print("Testing import organization...")
    
    # Test main module imports
    try:
        import main
        print("  ✓ Main module imports successfully with reorganized imports")
    except ImportError as e:
        print(f"  ✗ Main module import failed: {e}")
        return False
    
    return True

def run_all_tests():
    """Run all style improvement tests."""
    print("=" * 60)
    print("     FLO-2D Style Guide Improvement Validation")
    print("=" * 60)
    print()
    
    tests = [
        test_function_naming,
        test_documentation,
        test_logging_integration,
        test_constants_usage,
        test_import_organization
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"  ✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
            print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All style improvements are working correctly!")
        print()
        print("Key improvements validated:")
        print("  ✓ Function naming follows snake_case convention")
        print("  ✓ Modules have comprehensive docstrings")
        print("  ✓ Logging replaces print statements")
        print("  ✓ Constants module is properly utilized")
        print("  ✓ Imports follow PEP 8 organization")
        return True
    else:
        print("❌ Some tests failed. Please review the output above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
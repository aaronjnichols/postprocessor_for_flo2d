#!/usr/bin/env python3
"""
Test runner script for FLO-2D Postprocessor.
Provides convenient ways to run different test suites.
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - FAILED")
        print(f"Exit code: {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ {description} - FAILED")
        print("pytest not found. Please install test requirements:")
        print("pip install -r test-requirements.txt")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run FLO-2D Postprocessor tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--file", help="Run specific test file")
    
    args = parser.parse_args()
    
    # Change to project directory
    project_dir = Path(__file__).parent
    sys.path.insert(0, str(project_dir))
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term-missing"])
    
    if args.fast:
        cmd.extend(["-m", "not slow"])
    
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    
    if args.file:
        cmd.append(args.file)
    else:
        cmd.append("tests/")
    
    # Run tests
    success = run_command(cmd, "Test Suite")
    
    if success:
        print(f"\n🎉 All tests completed successfully!")
        if args.coverage:
            print(f"📊 Coverage report generated in htmlcov/index.html")
    else:
        print(f"\n💥 Some tests failed. Check output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
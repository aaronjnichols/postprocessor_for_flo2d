"""
Quickly generate the SWMM outfalls Excel and PDF for a given model folder.

Usage:
    python scripts/quick_outfall_excel.py C:\\path\\to\\model_folder
"""

import os
import sys
from pathlib import Path

# Ensure repo root on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from extraction.out.swmm_outfalls_rpt import extract_swmm_outfalls_rpt
from reporting.spreadsheets.swmm_outfalls_spreadsheet import swmm_outfalls_spreadsheet_and_plots


def main(folder: str) -> int:
    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}")
        return 2
    data = extract_swmm_outfalls_rpt(folder)
    paths = swmm_outfalls_spreadsheet_and_plots(folder, data)
    print("Created:", paths)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/quick_outfall_excel.py <model_folder>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))

"""
Verify SWMM outfalls attribute column order using a given model folder or RPT path.

Usage:
    python scripts/verify_outfalls_order.py "C:\\path\\to\\swmm.RPT"
    python scripts/verify_outfalls_order.py "C:\\path\\to\\model_folder"

Outputs ordered column list and a preview of the attribute table for outfalls.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

import pandas as pd


def main(arg_path: str) -> int:
    # Resolve folder and input file
    if os.path.isfile(arg_path) and arg_path.lower().endswith('.rpt'):
        folder = os.path.dirname(arg_path)
    else:
        folder = arg_path

    if not os.path.isdir(folder):
        print(f"ERROR: Folder not found: {folder}")
        return 2

    # Locate SWMM.inp in folder (case-insensitive)
    inp_path = None
    for name in os.listdir(folder):
        if name.lower() == 'swmm.inp':
            inp_path = os.path.join(folder, name)
            break
    if inp_path is None:
        # Fallback: any .inp named like swmm*.inp
        candidates = [n for n in os.listdir(folder) if n.lower().endswith('.inp') and n.lower().startswith('swmm')]
        if candidates:
            inp_path = os.path.join(folder, candidates[0])
    if inp_path is None or not os.path.isfile(inp_path):
        print(f"ERROR: SWMM input file not found in folder: {folder}")
        return 3

    # Ensure repository root is on sys.path for absolute imports
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Import project modules lazily
    try:
        from extraction.dat.swmm_inp_extraction import extract_swmm_inp
        from extraction.out.swmm_outfalls_rpt import extract_swmm_outfalls_rpt
        from processing.vectorization.swmm_schema import (
            canonicalize_outfall_summary,
            apply_outfall_schema,
        )
    except Exception as e:
        print("ERROR: Failed to import project modules:")
        traceback.print_exc()
        return 4

    # Extract geometry from SWMM.inp (EPSG not critical for attribute order)
    EPSG = 4326
    swmm_data = extract_swmm_inp(inp_path, EPSG)
    outfalls_gdf = swmm_data.get('outfalls')
    if outfalls_gdf is None or outfalls_gdf.empty:
        print("ERROR: No outfalls geometry extracted from SWMM.inp")
        return 5

    # Extract RPT outfalls summary
    rpt = extract_swmm_outfalls_rpt(folder)
    merged_results = rpt.get('merged_results', pd.DataFrame())
    outfalls_summary = canonicalize_outfall_summary(merged_results)

    # Merge like vectorization does (name-normalized) and apply schema
    odf = outfalls_gdf.copy()
    if outfalls_summary is not None and not outfalls_summary.empty:
        sdf = outfalls_summary.copy()
        odf['_key'] = odf['name'].astype(str).str.strip().str.upper()
        join_col = 'name' if 'name' in sdf.columns else 'node_id'
        sdf['_key'] = sdf[join_col].astype(str).str.strip().str.upper()
        merged_outfalls = odf.merge(sdf, on='_key', how='left')
        if 'name' not in merged_outfalls.columns and 'name_x' in merged_outfalls.columns:
            merged_outfalls = merged_outfalls.rename(columns={'name_x': 'name'})
        if 'name_y' in merged_outfalls.columns:
            merged_outfalls = merged_outfalls.drop(columns=['name_y'])
        merged_outfalls = merged_outfalls.drop(columns=['_key'])
    else:
        merged_outfalls = odf

    enhanced_outfalls = apply_outfall_schema(merged_outfalls)

    # Print ordered columns and a preview of the attribute table
    cols = [c for c in enhanced_outfalls.columns if c != 'geometry']
    print("Ordered columns (geometry omitted):")
    print(cols)
    print("\nPreview (first 10 rows):")
    # Display as a simple table without geometry
    preview = pd.DataFrame(enhanced_outfalls.drop(columns=['geometry']).head(10))
    # Limit float precision for readability
    with pd.option_context('display.max_columns', None, 'display.width', 160, 'display.max_colwidth', 40, 'display.precision', 4):
        print(preview)

    # Save a GeoPackage to the model folder for GIS inspection
    try:
        gpkg_path = os.path.join(folder, 'swmm_outfalls.gpkg')
        # Ensure CRS is set
        if enhanced_outfalls.crs is None:
            enhanced_outfalls.set_crs(epsg=EPSG, inplace=True)
        enhanced_outfalls.to_file(gpkg_path, layer='outfalls', driver='GPKG')
        print(f"\nSaved GeoPackage: {gpkg_path}")
    except Exception:
        print("\nWARNING: Failed to write GeoPackage (GPKG):")
        traceback.print_exc()
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_outfalls_order.py <path_to_swmm.RPT_or_folder>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))

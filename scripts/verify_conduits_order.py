"""
Verify SWMM conduits (links) attribute column order using a given model folder.

Usage:
    python scripts/verify_conduits_order.py "C:\\path\\to\\model_folder"

Outputs ordered column list and a preview of the attribute table for conduits,
and writes a GeoPackage layer for GIS inspection.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import traceback

import pandas as pd


def main(folder: str) -> int:
    if not os.path.isdir(folder):
        print(f"ERROR: Folder not found: {folder}")
        return 2

    # Repo imports
    try:
        repo_root = Path(__file__).resolve().parents[1]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from extraction.dat.swmm_inp_extraction import extract_swmm_inp
        from extraction.out.swmm_links_rpt import extract_swmmlinks_rpt
        from processing.vectorization.swmm_schema import (
            canonicalize_links_summary,
            apply_link_schema,
        )
    except Exception:
        traceback.print_exc()
        return 3

    # Find SWMM.inp
    inp_path = None
    for name in os.listdir(folder):
        if name.lower() == 'swmm.inp':
            inp_path = os.path.join(folder, name)
            break
    if inp_path is None:
        cands = [n for n in os.listdir(folder) if n.lower().endswith('.inp')]
        if cands:
            inp_path = os.path.join(folder, cands[0])
    if inp_path is None or not os.path.isfile(inp_path):
        print("ERROR: SWMM.inp not found")
        return 4

    EPSG = 4326
    swmm_data = extract_swmm_inp(inp_path, EPSG)
    cdf = swmm_data.get('conduits')
    if cdf is None or cdf.empty:
        print("ERROR: No conduits geometry extracted from SWMM.inp")
        return 5

    rpt = extract_swmmlinks_rpt(folder)
    merged_results = rpt.get('merged_results', pd.DataFrame())
    links_summary = canonicalize_links_summary(merged_results)

    # Merge on normalized name
    gdf = cdf.copy()
    if links_summary is not None and not links_summary.empty:
        sdf = links_summary.copy()
        gdf['_key'] = gdf['name'].astype(str).str.strip().str.upper()
        join_col = 'name' if 'name' in sdf.columns else 'link_id'
        sdf['_key'] = sdf[join_col].astype(str).str.strip().str.upper()
        merged = gdf.merge(sdf, on='_key', how='left')
        if 'name' not in merged.columns and 'name_x' in merged.columns:
            merged = merged.rename(columns={'name_x': 'name'})
        if 'name_y' in merged.columns:
            merged = merged.drop(columns=['name_y'])
        merged = merged.drop(columns=['_key'])
    else:
        merged = gdf

    print('Merged columns:', list(merged.columns))
    enhanced = apply_link_schema(merged)

    cols = [c for c in enhanced.columns if c != 'geometry']
    print("Ordered columns (geometry omitted):")
    print(cols)

    print("\nPreview (first 10 rows):")
    preview = pd.DataFrame(enhanced.drop(columns=['geometry']).head(10))
    with pd.option_context('display.max_columns', None, 'display.width', 200, 'display.max_colwidth', 40, 'display.precision', 4):
        print(preview)

    try:
        gpkg_path = os.path.join(folder, 'swmm_conduits.gpkg')
        if enhanced.crs is None:
            enhanced.set_crs(epsg=EPSG, inplace=True)
        enhanced.to_file(gpkg_path, layer='conduits', driver='GPKG')
        print(f"\nSaved GeoPackage: {gpkg_path}")
    except Exception:
        print("\nWARNING: Failed to write GeoPackage (GPKG):")
        traceback.print_exc()
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_conduits_order.py <model_folder>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))

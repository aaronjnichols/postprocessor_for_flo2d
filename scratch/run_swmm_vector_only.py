import sys, os
sys.path.append(os.getcwd())
import os, pandas as pd
from extraction.dat.swmm_inp_extraction import extract_swmm_inp
from extraction.out.swmm_outfalls_rpt import extract_swmm_outfalls_rpt
from extraction.out.swmm_junctions_rpt import extract_swmm_junctions_rpt
from extraction.out.swmmlinks_rpt import extract_swmmlinks_rpt
from processing.vectorization.swmm_schema import (
    canonicalize_outfall_summary, canonicalize_junctions_summary, canonicalize_links_summary
)
from processing.vectorization.swmm_vectorization import create_swmm_shapefiles

model_dir = r'C:\\_hh_models\\flo2d\\detroit_basin_100y24h_prop'
shp_out = os.path.join(model_dir, 'flo2d_shp')

swmm_inp = os.path.join(model_dir, 'SWMM.INP')
swmm_data = extract_swmm_inp(swmm_inp, 2898)

outfalls_data = extract_swmm_outfalls_rpt(model_dir)
outfalls_summary = canonicalize_outfall_summary(outfalls_data.get('merged_results'))

junctions_data = extract_swmm_junctions_rpt(model_dir)
junctions_summary = canonicalize_junctions_summary(junctions_data.get('merged_results'))

links_data = extract_swmmlinks_rpt(model_dir)
links_summary = canonicalize_links_summary(links_data.get('merged_results'))

created = create_swmm_shapefiles(
    swmm_data,
    shp_out,
    output_format='Shapefile',
    junctions_summary=junctions_summary,
    outfalls_summary=outfalls_summary,
    links_summary=links_summary,
)
print('Created:', created)

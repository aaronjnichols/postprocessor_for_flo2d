import os, sys
import pandas as pd
rpt_path = r'C:\_hh_models\flo2d\detroit_basin_100y24h_prop\swmm.RPT'
folder = os.path.dirname(rpt_path)
sys.path.insert(0, os.getcwd())
from extraction.out.swmmnodes_rpt import extract_swmmnodes_rpt
nodes_data = extract_swmmnodes_rpt(folder)
merged = nodes_data.get('merged_results')
outfalls_nodes_df = merged[merged['type']=='OUTFALL'].copy()
outfall_loading = nodes_data.get('outfall_loading')
load_df = pd.DataFrame.from_dict(outfall_loading, orient='index') if isinstance(outfall_loading, dict) and outfall_loading else pd.DataFrame()
if not load_df.empty:
    load_df.index.name='node_id'; load_df.reset_index(inplace=True)

outfalls_summary = outfalls_nodes_df
if not load_df.empty:
    outfalls_summary = pd.merge(outfalls_nodes_df, load_df, on='node_id', how='left')

print('OUTFALLS_SUMMARY_COLS', list(outfalls_summary.columns))

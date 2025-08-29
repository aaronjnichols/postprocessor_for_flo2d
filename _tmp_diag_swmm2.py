import os, sys
import pandas as pd
rpt_path = r'C:\_hh_models\flo2d\detroit_basin_100y24h_prop\swmm.RPT'
folder = os.path.dirname(rpt_path)
inp_path = os.path.join(folder,'SWMM.inp')
sys.path.insert(0, os.getcwd())
from extraction.out.swmmnodes_rpt import extract_swmmnodes_rpt
nodes_data = extract_swmmnodes_rpt(folder)
merged = nodes_data.get('merged_results')
outfalls_nodes_df = merged[merged['type']=='OUTFALL'].copy()
outfall_loading = nodes_data.get('outfall_loading')
load_df = pd.DataFrame.from_dict(outfall_loading, orient='index') if isinstance(outfall_loading, dict) and outfall_loading else pd.DataFrame()
if not load_df.empty:
    load_df.index.name='node_id'; load_df.reset_index(inplace=True)

print('HAS_LOAD', not load_df.empty)
print('IN_LOAD_TARGET', any(load_df['node_id'].astype(str).str.upper()=='O-ST-OUT-10-55-002') if not load_df.empty else False)
print('IN_NODE_TARGET', any(outfalls_nodes_df['node_id'].astype(str).str.upper()=='O-ST-OUT-10-55-002'))

if not load_df.empty:
    left = outfalls_nodes_df[['node_id']].copy(); left['key']=left['node_id'].astype(str).str.strip().str.upper()
    right = load_df[['node_id']].copy(); right['key']=right['node_id'].astype(str).str.strip().str.upper()
    inter = set(left['key']).intersection(set(right['key']))
    print('INTERSECTION_COUNT', len(inter))
    print('TARGET_IN_INTERSECTION', 'O-ST-OUT-10-55-002' in inter)

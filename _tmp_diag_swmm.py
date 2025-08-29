import os, sys
import pandas as pd
rpt_path = r'C:\_hh_models\flo2d\detroit_basin_100y24h_prop\swmm.RPT'
folder = os.path.dirname(rpt_path)
# find INP
inp_path = None
for cand in ['SWMM.inp','swmm.inp','model.inp']:
    p = os.path.join(folder, cand)
    if os.path.exists(p):
        inp_path = p
        break
print('USING_INP', os.path.basename(inp_path) if inp_path else 'NOT_FOUND')
if not inp_path:
    sys.exit(0)
# import repo modules
sys.path.insert(0, os.getcwd())
from extraction.dat.swmm_inp_extraction import extract_swmm_inp
from extraction.out.swmmnodes_rpt import extract_swmmnodes_rpt
from processing.vectorization.swmm_schema import apply_outfall_schema

swmm_data = extract_swmm_inp(inp_path, 4326)
outfalls_gdf = swmm_data.get('outfalls')
print('GEOM_COLS', list(outfalls_gdf.columns))
print('GEOM_SAMPLE_NAMES', outfalls_gdf['name'].astype(str).head(3).tolist())

nodes_data = extract_swmmnodes_rpt(folder)
merged = nodes_data.get('merged_results')
print('MERGED_RESULTS_COLS', merged.columns[:20].tolist())

outfalls_nodes_df = merged[merged['type']=='OUTFALL'].copy()
# loading
outfall_loading = nodes_data.get('outfall_loading')
load_df = None
if isinstance(outfall_loading, dict) and outfall_loading:
    load_df = pd.DataFrame.from_dict(outfall_loading, orient='index')
    load_df.index.name = 'node_id'
    load_df.reset_index(inplace=True)
    print('LOAD_COLS', list(load_df.columns))
else:
    print('NO_LOADING_SUMMARY')

outfalls_summary = outfalls_nodes_df
if load_df is not None:
    outfalls_summary = pd.merge(outfalls_nodes_df, load_df, on='node_id', how='left')

rename_map = {
    'inv_elev': 'inv_elev',
    'max_depth': 'max_depth_cap',
    'pond_area': 'pond_area',
    'ext_inflow': 'ext_inflow',
    'Avg_Depth': 'avg_depth',
    'Max_Depth': 'max_depth_obs',
    'Max_HGL': 'max_hgl',
    'Time_of_Max_Depth': 'time_max_depth',
    'Max_Lateral_Inflow': 'max_lat_inflow',
    'Max_Total_Inflow': 'max_tot_inflow',
    'Time_of_Max_Inflow': 'time_max_inflow',
    'Lateral_Inflow_Volume': 'lat_inflow_vol',
    'Total_Inflow_Volume': 'tot_inflow_vol',
    'Flow_Freq_Pcnt': 'flow_freq_pcnt',
    'Avg_Flow_CFS': 'avg_flow_cfs',
    'Max_Flow_CFS': 'max_flow_cfs',
    'Total_Volume_MG': 'total_volume_mg',
}
existing = {k:v for k,v in rename_map.items() if k in outfalls_summary.columns}
outfalls_summary = outfalls_summary.rename(columns=existing)
outfalls_summary['name'] = outfalls_summary['node_id'].astype(str).str.strip()
print('SUMMARY_CANON_COLS', [c for c in ['inv_elev','max_depth_cap','pond_area','ext_inflow','avg_depth','max_depth_obs','max_hgl','time_max_depth','flow_freq_pcnt','avg_flow_cfs','max_flow_cfs','total_volume_mg'] if c in outfalls_summary.columns])
row = outfalls_summary[outfalls_summary['name'].str.upper()=='O-ST-OUT-10-55-002']
print('SUMMARY_TARGET_ROWS', len(row))
if not row.empty:
    print(row[['name','inv_elev','max_depth_cap','pond_area','ext_inflow','avg_depth','max_depth_obs','max_hgl','time_max_depth','flow_freq_pcnt','avg_flow_cfs','max_flow_cfs','total_volume_mg']].to_string(index=False))

# merge by name normalized
jdf = outfalls_gdf.copy()
jdf['_key'] = jdf['name'].astype(str).str.strip().str.upper()
outfalls_summary['_key'] = outfalls_summary['name'].astype(str).str.strip().str.upper()
merged_outfalls = jdf.merge(outfalls_summary, on='_key', how='left')
print('MERGED_HAS_CANON', {c: (c in merged_outfalls.columns) for c in ['inv_elev','max_depth_cap','pond_area','ext_inflow','avg_depth','max_depth_obs','max_hgl','time_max_depth','flow_freq_pcnt','avg_flow_cfs','max_flow_cfs','total_volume_mg']})
mask = merged_outfalls['name_x'].str.upper()=='O-ST-OUT-10-55-002'
print('MERGED_TARGET_ROWS', int(mask.sum()))
if mask.any():
    mrow = merged_outfalls.loc[mask, ['name_x','inv_elev','max_depth_cap','pond_area','ext_inflow','avg_depth','max_depth_obs','max_hgl','time_max_depth','flow_freq_pcnt','avg_flow_cfs','max_flow_cfs','total_volume_mg']]
    print(mrow.to_string(index=False))

# schema
from processing.vectorization.swmm_schema import apply_outfall_schema
out_df = apply_outfall_schema(merged_outfalls)
print('SCHEMA_COLS', list(out_df.columns))
mask = (out_df['name'].astype(str).str.upper()=='O-ST-OUT-10-55-002') if 'name' in out_df.columns else pd.Series()
print('SCHEMA_TARGET_ROWS', int(mask.sum()) if hasattr(mask,'sum') else 0)
if hasattr(mask,'any') and mask.any():
    print(out_df.loc[mask].to_string(index=False))

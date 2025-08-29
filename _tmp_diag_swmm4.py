import os, sys
import pandas as pd
rpt_path = r'C:\_hh_models\flo2d\detroit_basin_100y24h_prop\swmm.RPT'
folder = os.path.dirname(rpt_path)
# extract
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

# canonicalize
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
}
existing = {k:v for k,v in rename_map.items() if k in outfalls_summary.columns}
outfalls_summary = outfalls_summary.rename(columns=existing)
# coalesce loading columns
for srcs, tgt in [
    (['flow_freq_pcnt','Flow_Freq_Pcnt','Flow_Freq_Pcnt_x','Flow_Freq_Pcnt_y'], 'flow_freq_pcnt'),
    (['avg_flow_cfs','Avg_Flow_CFS','Avg_Flow_CFS_x','Avg_Flow_CFS_y'], 'avg_flow_cfs'),
    (['max_flow_cfs','Max_Flow_CFS','Max_Flow_CFS_x','Max_Flow_CFS_y'], 'max_flow_cfs'),
    (['total_volume_mg','Total_Volume_MG','Total_Volume_MG_x','Total_Volume_MG_y'], 'total_volume_mg'),
]:
    for s in srcs:
        if s in outfalls_summary.columns:
            outfalls_summary[tgt] = outfalls_summary[s]
            break

outfalls_summary['name'] = outfalls_summary['node_id'].astype(str).str.strip()
print('CANON_AFTER', [c for c in ['flow_freq_pcnt','avg_flow_cfs','max_flow_cfs','total_volume_mg'] if c in outfalls_summary.columns])
row = outfalls_summary[outfalls_summary['name'].str.upper()=='O-ST-OUT-10-55-002']
print('ROWS', len(row))
if not row.empty:
    print(row[['name','flow_freq_pcnt','avg_flow_cfs','max_flow_cfs','total_volume_mg']].to_string(index=False))

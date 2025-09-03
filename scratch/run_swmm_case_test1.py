import sys, os, pandas as pd
sys.path.append(os.getcwd())
from extraction.dat.swmm_inp_extraction import extract_swmm_inp
from extraction.out.swmm_outfalls_rpt import extract_swmm_outfalls_rpt
from processing.vectorization.swmm_schema import canonicalize_outfall_summary, apply_outfall_schema
import geopandas as gpd

model_dir = r'scratch\\swmm_case_test1'
print('Model dir:', model_dir)
inp_path = os.path.join(model_dir, 'SWMM.INP')

# Extract geometry
swmm_data = extract_swmm_inp(inp_path, 2898)
print('Geometry outfalls columns:', list(swmm_data['outfalls'].columns))
print('Outfall names:', swmm_data['outfalls']['name'].tolist())

# Extract RPT outfalls summary
out = extract_swmm_outfalls_rpt(model_dir)
merged = out.get('merged_results', pd.DataFrame())
print('RPT merged_results shape:', merged.shape)
print('RPT merged_results columns:', list(merged.columns))
print('RPT merged_results head:\n', merged.head(3))

# Canonicalize then simulate merge as in vectorization
canon = canonicalize_outfall_summary(merged)
print('Canonicalized columns:', list(canon.columns))

# Perform merge similar to swmm_vectorization for outfalls
odf = swmm_data['outfalls'].copy()
sdf = canon.copy()
# normalized key
odf['_key'] = odf['name'].astype(str).str.strip().str.upper()
join_col = 'name' if 'name' in sdf.columns else 'node_id'
sdf['_key'] = sdf[join_col].astype(str).str.strip().str.upper()
merged_outfalls = odf.merge(sdf, on='_key', how='left')
if 'name' not in merged_outfalls.columns and 'name_x' in merged_outfalls.columns:
    merged_outfalls = merged_outfalls.rename(columns={'name_x':'name'})
if 'name_y' in merged_outfalls.columns:
    merged_outfalls = merged_outfalls.drop(columns=['name_y'])
merged_outfalls = merged_outfalls.drop(columns=['_key'])

print('Merged outfalls columns:', list(merged_outfalls.columns))

# Apply outfall schema to get final attribute set
final_gdf = apply_outfall_schema(gpd.GeoDataFrame(merged_outfalls, geometry=odf.geometry, crs=odf.crs))
print('Final outfall attribute columns:', list(final_gdf.columns))
print('Final outfall attribute sample rows:\n', final_gdf[['name','avg_dep','dmax_obs','max_hgl','t_max_dep']].head())

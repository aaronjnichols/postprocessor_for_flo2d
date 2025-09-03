import geopandas as gpd
p=r'C:\\_hh_models\\flo2d\\detroit_basin_100y24h_prop\\flo2d_shp\\outfalls.shp'
gdf=gpd.read_file(p)
cols=['avg_dep','dmax_obs','max_hgl','t_max_dep']
print('Exists:', {c: (c in gdf.columns) for c in cols})
for c in cols:
    if c in gdf.columns:
        print(c, 'non-null:', int(gdf[c].notna().sum()), 'of', len(gdf))

"""
SWMM output schema utilities.

This module defines short, Shapefile-safe (<=10 chars) attribute names and
applies a consistent, deduplicated field set to SWMM vector layers.

Always emits the full deduplicated set (no profiles).
"""

from __future__ import annotations

from typing import Dict, List

import logging
import pandas as pd
import geopandas as gpd


# Shapefile-safe maximum field name length
MAX_FIELD_LEN = 10


def _first_present(df: pd.DataFrame, candidates: List[str]) -> str | None:
    """Return the first column name from candidates that exists in df."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def apply_junction_schema(merged_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Apply short, deduplicated attribute schema to a merged SWMM junctions GeoDataFrame.

    Expects a GeoDataFrame produced by merging SWMM INP junctions with SWMM RPT summary
    (as done in swmm_vectorization._merge_rpt_summary_data).

    Returns
    -------
    GeoDataFrame
        A GeoDataFrame with short field names (<=10 chars), deduplicated so that
        INP design values are preferred and RPT provides observed metrics.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')

    if merged_gdf is None or merged_gdf.empty:
        return merged_gdf

    df = merged_gdf.copy()

    # Build the output columns progressively to control order
    out_cols: Dict[str, pd.Series] = {}

    # Identity
    if 'name' in df.columns:
        out_cols['name'] = df['name']
    # RPT type (junction/outfall) if present
    if 'type' in df.columns:
        out_cols['j_type'] = df['type']

    # INP (design) fields — prefer these when duplicated by RPT
    if 'invert_elevation' in df.columns:
        out_cols['z_inv'] = pd.to_numeric(df['invert_elevation'], errors='coerce')
    if 'max_depth' in df.columns:
        out_cols['dmax_cap'] = pd.to_numeric(df['max_depth'], errors='coerce')
    if 'init_depth' in df.columns:
        out_cols['dinit'] = pd.to_numeric(df['init_depth'], errors='coerce')
    if 'surcharge_depth' in df.columns:
        out_cols['dsurch'] = pd.to_numeric(df['surcharge_depth'], errors='coerce')
    if 'ponded_area' in df.columns:
        out_cols['pond_area'] = pd.to_numeric(df['ponded_area'], errors='coerce')

    # RPT (observed) — prefer these only where there is no INP equivalent or where semantics differ
    # Continuity error
    cont_err_col = _first_present(df, ['Continuity_Error_Pcnt', 'continuity_error_pcnt'])
    if cont_err_col:
        out_cols['cont_err'] = pd.to_numeric(df[cont_err_col], errors='coerce')

    # Depth summary
    if 'Avg_Depth' in df.columns:
        out_cols['avg_dep'] = pd.to_numeric(df['Avg_Depth'], errors='coerce')
    # Max depth observed: prefer explicit RPT suffix then summary max depth
    dmax_obs_src = _first_present(df, ['max_depth_rpt', 'Max_Depth'])
    if dmax_obs_src:
        out_cols['dmax_obs'] = pd.to_numeric(df[dmax_obs_src], errors='coerce')
    # Max HGL
    max_hgl_src = _first_present(df, ['Max_HGL', 'max_hgl'])
    if max_hgl_src:
        out_cols['max_hgl'] = pd.to_numeric(df[max_hgl_src], errors='coerce')
    # Time of max depth
    t_md_src = _first_present(df, ['Time_of_Max_Depth', 't_max_depth'])
    if t_md_src:
        out_cols['t_max_dep'] = df[t_md_src]

    # Inflow summary
    if 'Max_Lateral_Inflow' in df.columns:
        out_cols['lat_inflw'] = pd.to_numeric(df['Max_Lateral_Inflow'], errors='coerce')
    if 'Max_Total_Inflow' in df.columns:
        out_cols['tot_inflw'] = pd.to_numeric(df['Max_Total_Inflow'], errors='coerce')
    t_mi_src = _first_present(df, ['Time_of_Max_Inflow', 't_tot_inflw'])
    if t_mi_src:
        out_cols['t_max_inf'] = df[t_mi_src]
    if 'Lateral_Inflow_Volume' in df.columns:
        out_cols['latinflvol'] = pd.to_numeric(df['Lateral_Inflow_Volume'], errors='coerce')
    if 'Total_Inflow_Volume' in df.columns:
        out_cols['totinflvol'] = pd.to_numeric(df['Total_Inflow_Volume'], errors='coerce')

    # Surcharge summary
    if 'Hours_Surcharged' in df.columns:
        out_cols['hrs_surch'] = pd.to_numeric(df['Hours_Surcharged'], errors='coerce')
    if 'Max_Height_Above_Crown' in df.columns:
        out_cols['h_abv_crwn'] = pd.to_numeric(df['Max_Height_Above_Crown'], errors='coerce')
    if 'Min_Depth_Below_Rim' in df.columns:
        out_cols['d_blw_rim'] = pd.to_numeric(df['Min_Depth_Below_Rim'], errors='coerce')

    # Flooding summary
    if 'Hours_Flooded' in df.columns:
        out_cols['hr_flooded'] = pd.to_numeric(df['Hours_Flooded'], errors='coerce')
    if 'Max_Flooding_Rate' in df.columns:
        out_cols['flood_rate'] = pd.to_numeric(df['Max_Flooding_Rate'], errors='coerce')
    t_flood_src = _first_present(df, ['Time_of_Max_Flooding', 't_flood'])
    if t_flood_src:
        out_cols['t_flood'] = df[t_flood_src]
    if 'Total_Flood_Volume' in df.columns:
        out_cols['flood_vol'] = pd.to_numeric(df['Total_Flood_Volume'], errors='coerce')
    if 'Max_Ponded_Depth' in df.columns:
        out_cols['ponded_dep'] = pd.to_numeric(df['Max_Ponded_Depth'], errors='coerce')

    # Build the output GeoDataFrame with selected columns (preserve geometry)
    ordered = [
        'name', 'j_type',
        'z_inv', 'dmax_cap', 'dinit', 'dsurch', 'pond_area',
        'cont_err',
        'avg_dep', 'dmax_obs', 'max_hgl', 't_max_dep',
        'lat_inflw', 'tot_inflw', 't_max_inf', 'latinflvol', 'totinflvol',
        'hrs_surch', 'h_abv_crwn', 'd_blw_rim',
        'hr_flooded', 'flood_rate', 't_flood', 'flood_vol', 'ponded_dep',
    ]

    cols_present = [c for c in ordered if c in out_cols]
    out_df = gpd.GeoDataFrame({c: out_cols[c] for c in cols_present}, geometry=df.geometry, crs=df.crs)

    # Enforce field name length (defensive; schema is already <=10)
    too_long = [c for c in out_df.columns if c != 'geometry' and len(c) > MAX_FIELD_LEN]
    if too_long:
        logger.warning(f"SWMM junction fields over {MAX_FIELD_LEN} chars (will be truncated by drivers): {too_long}")

    return out_df


def apply_outfall_schema(merged_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Apply short, deduplicated attribute schema to SWMM outfalls GeoDataFrame.

    INP fields kept with short names; RPT loading metrics mapped to short names.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    if merged_gdf is None or merged_gdf.empty:
        return merged_gdf

    df = merged_gdf.copy()
    out_cols: Dict[str, pd.Series] = {}

    # Identity
    if 'name' in df.columns:
        out_cols['name'] = df['name']

    # INP design
    if 'invert_elevation' in df.columns:
        out_cols['z_inv'] = pd.to_numeric(df['invert_elevation'], errors='coerce')
    # Outfall type
    otype_src = _first_present(df, ['outfall_type', 'Outfall_Type'])
    if otype_src:
        out_cols['o_type'] = df[otype_src]
    # Stage data (if present)
    stage_src = _first_present(df, ['stage_data', 'Stage_Data'])
    if stage_src:
        out_cols['stage'] = df[stage_src]
    # Tide gate
    tide_src = _first_present(df, ['tide_gate', 'Tide_Gate'])
    if tide_src:
        out_cols['tide_gate'] = df[tide_src]

    # RPT loading summary (Outfall Loading Summary)
    if 'Flow_Freq_Pcnt' in df.columns:
        out_cols['flwfrqpcnt'] = pd.to_numeric(df['Flow_Freq_Pcnt'], errors='coerce')
    if 'Avg_Flow_CFS' in df.columns:
        out_cols['avg_flow'] = pd.to_numeric(df['Avg_Flow_CFS'], errors='coerce')
    if 'Max_Flow_CFS' in df.columns:
        out_cols['max_flow'] = pd.to_numeric(df['Max_Flow_CFS'], errors='coerce')
    if 'Total_Volume_MG' in df.columns:
        out_cols['tot_vol_mg'] = pd.to_numeric(df['Total_Volume_MG'], errors='coerce')

    # RPT node-based observed metrics (outfalls appear in node sections too)
    # Depth summary
    if 'Avg_Depth' in df.columns:
        out_cols['avg_dep'] = pd.to_numeric(df['Avg_Depth'], errors='coerce')
    dmax_obs_src = _first_present(df, ['max_depth_rpt', 'Max_Depth'])
    if dmax_obs_src:
        out_cols['dmax_obs'] = pd.to_numeric(df[dmax_obs_src], errors='coerce')
    max_hgl_src = _first_present(df, ['Max_HGL', 'max_hgl'])
    if max_hgl_src:
        out_cols['max_hgl'] = pd.to_numeric(df[max_hgl_src], errors='coerce')
    t_md_src = _first_present(df, ['Time_of_Max_Depth', 't_max_depth'])
    if t_md_src:
        out_cols['t_max_dep'] = df[t_md_src]

    # Inflow summary
    if 'Max_Lateral_Inflow' in df.columns:
        out_cols['lat_inflw'] = pd.to_numeric(df['Max_Lateral_Inflow'], errors='coerce')
    if 'Max_Total_Inflow' in df.columns:
        out_cols['tot_inflw'] = pd.to_numeric(df['Max_Total_Inflow'], errors='coerce')
    t_mi_src = _first_present(df, ['Time_of_Max_Inflow', 't_tot_inflw'])
    if t_mi_src:
        out_cols['t_max_inf'] = df[t_mi_src]
    if 'Lateral_Inflow_Volume' in df.columns:
        out_cols['latinflvol'] = pd.to_numeric(df['Lateral_Inflow_Volume'], errors='coerce')
    if 'Total_Inflow_Volume' in df.columns:
        out_cols['totinflvol'] = pd.to_numeric(df['Total_Inflow_Volume'], errors='coerce')

    # Surcharge and flooding summaries
    if 'Hours_Surcharged' in df.columns:
        out_cols['hrs_surch'] = pd.to_numeric(df['Hours_Surcharged'], errors='coerce')
    if 'Hours_Flooded' in df.columns:
        out_cols['hr_flooded'] = pd.to_numeric(df['Hours_Flooded'], errors='coerce')
    if 'Max_Flooding_Rate' in df.columns:
        out_cols['flood_rate'] = pd.to_numeric(df['Max_Flooding_Rate'], errors='coerce')
    t_flood_src = _first_present(df, ['Time_of_Max_Flooding', 't_flood'])
    if t_flood_src:
        out_cols['t_flood'] = df[t_flood_src]
    if 'Total_Flood_Volume' in df.columns:
        out_cols['flood_vol'] = pd.to_numeric(df['Total_Flood_Volume'], errors='coerce')
    if 'Max_Ponded_Depth' in df.columns:
        out_cols['ponded_dep'] = pd.to_numeric(df['Max_Ponded_Depth'], errors='coerce')

    ordered = [
        'name', 'o_type', 'z_inv', 'stage', 'tide_gate',
        'flwfrqpcnt', 'avg_flow', 'max_flow', 'tot_vol_mg',
        'avg_dep', 'dmax_obs', 'max_hgl', 't_max_dep',
        'lat_inflw', 'tot_inflw', 't_max_inf', 'latinflvol', 'totinflvol',
        'hrs_surch', 'hr_flooded', 'flood_rate', 't_flood', 'flood_vol', 'ponded_dep',
    ]
    cols_present = [c for c in ordered if c in out_cols]
    out_df = gpd.GeoDataFrame({c: out_cols[c] for c in cols_present}, geometry=df.geometry, crs=df.crs)

    too_long = [c for c in out_df.columns if c != 'geometry' and len(c) > MAX_FIELD_LEN]
    if too_long:
        logger.warning(f"SWMM outfall fields over {MAX_FIELD_LEN} chars: {too_long}")
    return out_df


def apply_link_schema(merged_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Apply short, deduplicated attribute schema to SWMM links (conduits) GeoDataFrame."""
    logger = logging.getLogger('FLO2D_Postprocessor')
    if merged_gdf is None or merged_gdf.empty:
        return merged_gdf

    df = merged_gdf.copy()
    out_cols: Dict[str, pd.Series] = {}

    # Identity
    name_src = _first_present(df, ['name', 'link_id'])
    if name_src:
        out_cols['name'] = df[name_src]

    # INP design/geometry fields
    frm_src = _first_present(df, ['from_node', 'from'])
    if frm_src:
        out_cols['from'] = df[frm_src]
    to_src = _first_present(df, ['to_node', 'to'])
    if to_src:
        out_cols['to'] = df[to_src]
    if 'length' in df.columns:
        out_cols['len'] = pd.to_numeric(df['length'], errors='coerce')
    # Manning's n (various casings)
    n_src = _first_present(df, ['mannings_n', 'Manning_N', 'manning_n'])
    if n_src:
        out_cols['n'] = pd.to_numeric(df[n_src], errors='coerce')
    if 'inlet_offset' in df.columns:
        out_cols['in_off'] = pd.to_numeric(df['inlet_offset'], errors='coerce')
    if 'outlet_offset' in df.columns:
        out_cols['out_off'] = pd.to_numeric(df['outlet_offset'], errors='coerce')
    if 'init_flow' in df.columns:
        out_cols['q_init'] = pd.to_numeric(df['init_flow'], errors='coerce')
    # Distinguish INP max flow vs RPT max flow
    if 'max_flow' in df.columns:
        out_cols['qmax_inp'] = pd.to_numeric(df['max_flow'], errors='coerce')

    # RPT link summary metrics (already short by design in extraction constants)
    # Try to pick RPT versions (suffix _rpt) when overlaps occurred during merge
    def pick(col: str) -> pd.Series | None:
        c = _first_present(df, [f"{col}_rpt", col])
        return df[c] if c and c in df.columns else None

    # Link type
    if 'type' in df.columns:
        out_cols['l_type'] = df['type']
    # Flow/velocity and timing
    for col_in, col_out in [
        ('max_flow', 'max_flow'),
        ('day_max', 'day_max'),
        ('time_max', 'time_max'),
        ('max_vel', 'max_vel'),
        ('flow_ratio', 'flow_ratio'),
        ('depth_rat', 'depth_rat'),
        ('hrs_full', 'hrs_full'),
        ('hrs_full_u', 'hrs_full_u'),
        ('hrs_full_d', 'hrs_full_d'),
        ('hrs_above', 'hrs_above'),
        ('hrs_cap', 'hrs_cap'),
        ('adj_len', 'adj_len'),
        ('dry_up', 'dry_up'),
        ('dry_down', 'dry_down'),
        ('dry_sub', 'dry_sub'),
        ('dry_sup', 'dry_sup'),
        ('crit_up', 'crit_up'),
        ('crit_down', 'crit_down'),
        ('froude', 'froude'),
        ('flow_chg', 'flow_chg'),
    ]:
        s = pick(col_in)
        if s is not None:
            out_cols[col_out] = pd.to_numeric(s, errors='coerce') if col_out not in ('time_max',) else s

    ordered = [
        'name', 'l_type', 'from', 'to', 'len', 'n', 'in_off', 'out_off', 'q_init', 'qmax_inp',
        'max_flow', 'day_max', 'time_max', 'max_vel', 'flow_ratio', 'depth_rat', 'hrs_full',
        'hrs_full_u', 'hrs_full_d', 'hrs_above', 'hrs_cap', 'adj_len', 'dry_up', 'dry_down',
        'dry_sub', 'dry_sup', 'crit_up', 'crit_down', 'froude', 'flow_chg',
    ]
    cols_present = [c for c in ordered if c in out_cols]
    out_df = gpd.GeoDataFrame({c: out_cols[c] for c in cols_present}, geometry=df.geometry, crs=df.crs)

    too_long = [c for c in out_df.columns if c != 'geometry' and len(c) > MAX_FIELD_LEN]
    if too_long:
        logger.warning(f"SWMM link fields over {MAX_FIELD_LEN} chars: {too_long}")
    return out_df

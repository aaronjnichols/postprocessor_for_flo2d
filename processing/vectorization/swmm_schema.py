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


def _resolve_rpt(df: pd.DataFrame, base: str) -> str | None:
    """Resolve a column from RPT-derived data with common variants.

    Tries these in order for the given base name:
    - exact, with '_rpt' suffix
    - lowercase, lowercase + '_rpt'
    - spaces replaced with underscores (both cases)
    - common merge suffixes ('_x', '_y') for each variant
    Returns the first matching column name or None.
    """
    variants: List[str] = []
    bases = [base, base.lower(), base.replace(' ', '_'), base.lower().replace(' ', '_')]
    for b in bases:
        variants.extend([b, f"{b}_rpt", f"{b}_x", f"{b}_y"]) 
    # Deduplicate preserving order
    seen = set()
    ordered = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            ordered.append(v)
    for v in ordered:
        if v in df.columns:
            return v
    return None


# ---------------------------------------------------------------------------
# Canonicalization helpers for RPT payloads
# ---------------------------------------------------------------------------

def canonicalize_outfall_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Rename RPT outfall summary columns to canonical names and set 'name'.

    Applies to a DataFrame built from Node Summary (+ Depth/Inflow summaries)
    left-joined with Outfall Loading Summary.
    """
    if df is None or df.empty:
        return df
    out = df.copy()

    rename_map = {
        # Node Summary
        'inv_elev': 'inv_elev',
        'max_depth': 'max_depth_cap',
        'pond_area': 'pond_area',
        'ext_inflow': 'ext_inflow',
        # Depth Summary
        'Avg_Depth': 'avg_depth',
        'Max_Depth': 'max_depth_obs',
        'Max_HGL': 'max_hgl',
        'Time_of_Max_Depth': 'time_max_depth',
        # Inflow Summary
        'Max_Lateral_Inflow': 'max_lat_inflow',
        'Max_Total_Inflow': 'max_tot_inflow',
        'Time_of_Max_Inflow': 'time_max_inflow',
        'Lateral_Inflow_Volume': 'lat_inflow_vol',
        'Total_Inflow_Volume': 'tot_inflow_vol',
        # Outfall Loading Summary
        'Flow_Freq_Pcnt': 'flow_freq_pcnt',
        'Avg_Flow_CFS': 'avg_flow_cfs',
        'Max_Flow_CFS': 'max_flow_cfs',
        'Total_Volume_MG': 'total_volume_mg',
    }
    existing = {k: v for k, v in rename_map.items() if k in out.columns}
    if existing:
        out = out.rename(columns=existing)

    # Coalesce suffixed loading fields if present
    def coalesce(df_: pd.DataFrame, outname: str, candidates: List[str]):
        for c in candidates:
            if c in df_.columns:
                df_[outname] = df_[c]
                return

    coalesce(out, 'flow_freq_pcnt', ['flow_freq_pcnt','Flow_Freq_Pcnt','Flow_Freq_Pcnt_x','Flow_Freq_Pcnt_y'])
    coalesce(out, 'avg_flow_cfs', ['avg_flow_cfs','Avg_Flow_CFS','Avg_Flow_CFS_x','Avg_Flow_CFS_y'])
    coalesce(out, 'max_flow_cfs', ['max_flow_cfs','Max_Flow_CFS','Max_Flow_CFS_x','Max_Flow_CFS_y'])
    coalesce(out, 'total_volume_mg', ['total_volume_mg','Total_Volume_MG','Total_Volume_MG_x','Total_Volume_MG_y'])

    # Canonical ID
    if 'node_id' in out.columns and 'name' not in out.columns:
        out['name'] = out['node_id'].astype(str).str.strip()
    return out


def canonicalize_junctions_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Rename RPT junction summary columns to canonical names and set 'name'."""
    if df is None or df.empty:
        return df
    out = df.copy()
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
        'Hours_Surcharged': 'hours_surcharged',
        'Hours_Flooded': 'hours_flooded',
        'Max_Flooding_Rate': 'max_flooding_rate',
        'Time_of_Max_Flooding': 'time_of_max_flooding',
        'Total_Flood_Volume': 'total_flood_volume',
        'Max_Ponded_Depth': 'max_ponded_depth',
    }
    existing = {k: v for k, v in rename_map.items() if k in out.columns}
    if existing:
        out = out.rename(columns=existing)
    if 'node_id' in out.columns and 'name' not in out.columns:
        out['name'] = out['node_id'].astype(str).str.strip()
    return out


def canonicalize_links_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Rename RPT links summary columns to canonical names and set 'name'."""
    if df is None or df.empty:
        return df
    out = df.copy()
    rename_map = {
        'link_id': 'name',
        'type': 'type',
        'max_flow': 'max_flow',
        'day_max': 'day_max',
        'time_max': 'time_max',
        'max_vel': 'max_vel',
        'flow_ratio': 'flow_ratio',
        'depth_rat': 'depth_rat',
        'hrs_full': 'hrs_full',
        'hrs_full_u': 'hrs_full_u',
        'hrs_full_d': 'hrs_full_d',
        'hrs_above': 'hrs_above',
        'hrs_cap': 'hrs_cap',
        'adj_len': 'adj_len',
        'dry_up': 'dry_up',
        'dry_down': 'dry_down',
        'dry_sub': 'dry_sub',
        'dry_sup': 'dry_sup',
        'crit_up': 'crit_up',
        'crit_down': 'crit_down',
        'froude': 'froude',
        'flow_chg': 'flow_chg',
    }
    existing = {k: v for k, v in rename_map.items() if k in out.columns}
    if existing:
        out = out.rename(columns=existing)
    if 'name' in out.columns:
        out['name'] = out['name'].astype(str).str.strip()
    return out


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
    avgd_src = _first_present(df, ['Avg_Depth', 'avg_depth'])
    if avgd_src:
        out_cols['avg_dep'] = pd.to_numeric(df[avgd_src], errors='coerce')
    # Max depth observed: prefer explicit RPT suffix then summary max depth
    dmax_obs_src = _first_present(df, ['max_depth_rpt', 'Max_Depth', 'max_depth_obs'])
    if dmax_obs_src:
        out_cols['dmax_obs'] = pd.to_numeric(df[dmax_obs_src], errors='coerce')
    # Max HGL
    max_hgl_src = _first_present(df, ['Max_HGL', 'max_hgl'])
    if max_hgl_src:
        out_cols['max_hgl'] = pd.to_numeric(df[max_hgl_src], errors='coerce')
    # Time of max depth
    t_md_src = _first_present(df, ['Time_of_Max_Depth', 'time_max_depth', 't_max_depth'])
    if t_md_src:
        out_cols['t_max_dep'] = df[t_md_src]

    # Inflow summary
    mli_src = _resolve_rpt(df, 'Max_Lateral_Inflow') or _first_present(df, ['max_lat_inflow'])
    if mli_src:
        out_cols['lat_inflw'] = pd.to_numeric(df[mli_src], errors='coerce')
    mti_src = _resolve_rpt(df, 'Max_Total_Inflow') or _first_present(df, ['max_tot_inflow'])
    if mti_src:
        out_cols['tot_inflw'] = pd.to_numeric(df[mti_src], errors='coerce')
    t_mi_src = _resolve_rpt(df, 'Time_of_Max_Inflow') or _first_present(df, ['time_max_inflow', 't_tot_inflw'])
    if t_mi_src:
        out_cols['t_max_inf'] = df[t_mi_src]
    liv_src = _resolve_rpt(df, 'Lateral_Inflow_Volume') or _first_present(df, ['lat_inflow_vol'])
    if liv_src:
        out_cols['latinflvol'] = pd.to_numeric(df[liv_src], errors='coerce')
    tiv_src = _resolve_rpt(df, 'Total_Inflow_Volume') or _first_present(df, ['tot_inflow_vol'])
    if tiv_src:
        out_cols['totinflvol'] = pd.to_numeric(df[tiv_src], errors='coerce')

    # Surcharge summary
    hs_src = _first_present(df, ['Hours_Surcharged', 'hours_surcharged'])
    if hs_src:
        out_cols['hrs_surch'] = pd.to_numeric(df[hs_src], errors='coerce')
    if 'Max_Height_Above_Crown' in df.columns:
        out_cols['h_abv_crwn'] = pd.to_numeric(df['Max_Height_Above_Crown'], errors='coerce')
    if 'Min_Depth_Below_Rim' in df.columns:
        out_cols['d_blw_rim'] = pd.to_numeric(df['Min_Depth_Below_Rim'], errors='coerce')

    # Flooding summary
    if 'Hours_Flooded' in df.columns or 'hours_flooded' in df.columns:
        hf_src = _first_present(df, ['Hours_Flooded', 'hours_flooded'])
        out_cols['hr_flooded'] = pd.to_numeric(df[hf_src], errors='coerce')
    mfr_src = _first_present(df, ['Max_Flooding_Rate', 'max_flooding_rate'])
    if mfr_src:
        out_cols['flood_rate'] = pd.to_numeric(df[mfr_src], errors='coerce')
    t_flood_src = _first_present(df, ['Time_of_Max_Flooding', 'time_of_max_flooding', 't_flood'])
    if t_flood_src:
        out_cols['t_flood'] = df[t_flood_src]
    tfv_src = _first_present(df, ['Total_Flood_Volume', 'total_flood_volume'])
    if tfv_src:
        out_cols['flood_vol'] = pd.to_numeric(df[tfv_src], errors='coerce')
    mpd_src = _first_present(df, ['Max_Ponded_Depth', 'max_ponded_depth'])
    if mpd_src:
        out_cols['ponded_dep'] = pd.to_numeric(df[mpd_src], errors='coerce')

    # Build the output GeoDataFrame with selected columns (preserve geometry)
    # Column ordering: INP [JUNCTIONS] first, then RPT sections in report order
    ordered = [
        # INP [JUNCTIONS]
        'name', 'z_inv', 'dmax_cap', 'dinit', 'dsurch', 'pond_area',
        # RPT Node Summary
        'j_type',
        # Highest Continuity Errors
        'cont_err',
        # Depth Summary
        'avg_dep', 'dmax_obs', 'max_hgl', 't_max_dep',
        # Inflow Summary
        'lat_inflw', 'tot_inflw', 't_max_inf', 'latinflvol', 'totinflvol',
        # Surcharge Summary
        'hrs_surch', 'h_abv_crwn', 'd_blw_rim',
        # Flooding Summary
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

    # Invert elevation: prefer RPT Node Summary (inv_elev), fallback to INP
    inv_src = _first_present(df, ['inv_elev', 'invert_elevation', 'Invert_Elevation'])
    if inv_src:
        out_cols['z_inv'] = pd.to_numeric(df[inv_src], errors='coerce')
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
    ff_src = _first_present(df, ['flow_freq_pcnt']) or _resolve_rpt(df, 'Flow_Freq_Pcnt')
    if ff_src:
        out_cols['flwfrqpcnt'] = pd.to_numeric(df[ff_src], errors='coerce')
    af_src = _first_present(df, ['avg_flow_cfs']) or _resolve_rpt(df, 'Avg_Flow_CFS')
    if af_src:
        out_cols['avg_flow'] = pd.to_numeric(df[af_src], errors='coerce')
    mf_src = _first_present(df, ['max_flow_cfs']) or _resolve_rpt(df, 'Max_Flow_CFS')
    if mf_src:
        out_cols['max_flow'] = pd.to_numeric(df[mf_src], errors='coerce')
    tv_src = _first_present(df, ['total_volume_mg']) or _resolve_rpt(df, 'Total_Volume_MG')
    if tv_src:
        out_cols['tot_vol_mg'] = pd.to_numeric(df[tv_src], errors='coerce')

    # RPT node-based observed metrics (outfalls appear in node sections too)
    # Depth summary
    ad_src = _first_present(df, ['avg_depth']) or _resolve_rpt(df, 'Avg_Depth')
    if ad_src:
        out_cols['avg_dep'] = pd.to_numeric(df[ad_src], errors='coerce')
    dmax_obs_src = _first_present(df, ['max_depth_obs']) or _resolve_rpt(df, 'Max_Depth')
    if dmax_obs_src:
        out_cols['dmax_obs'] = pd.to_numeric(df[dmax_obs_src], errors='coerce')
    max_hgl_src = _first_present(df, ['max_hgl']) or _resolve_rpt(df, 'Max_HGL')
    if max_hgl_src:
        out_cols['max_hgl'] = pd.to_numeric(df[max_hgl_src], errors='coerce')
    t_md_src = _first_present(df, ['time_max_depth','t_max_depth']) or _resolve_rpt(df, 'Time_of_Max_Depth')
    if t_md_src:
        out_cols['t_max_dep'] = df[t_md_src]

    # Node Summary design capacity/ponding for outfalls
    # Max depth capacity may be present as canonical 'max_depth_cap' or original 'max_depth'
    mdn_src = _first_present(df, ['max_depth_cap']) or _resolve_rpt(df, 'max_depth')
    if mdn_src:
        out_cols['dmax_cap'] = pd.to_numeric(df[mdn_src], errors='coerce')
    pan_src = _resolve_rpt(df, 'pond_area')
    if pan_src:
        out_cols['pond_area'] = pd.to_numeric(df[pan_src], errors='coerce')
    # External inflow from Node Summary
    ext_src = _resolve_rpt(df, 'ext_inflow') or _resolve_rpt(df, 'External_Inflow')
    if ext_src:
        out_cols['ext_in'] = pd.to_numeric(df[ext_src], errors='coerce')

    # Inflow summary (handle canonicalized and original names)
    mli_src = _resolve_rpt(df, 'Max_Lateral_Inflow') or _first_present(df, ['max_lat_inflow'])
    if mli_src:
        out_cols['lat_inflw'] = pd.to_numeric(df[mli_src], errors='coerce')
    mti_src = _resolve_rpt(df, 'Max_Total_Inflow') or _first_present(df, ['max_tot_inflow'])
    if mti_src:
        out_cols['tot_inflw'] = pd.to_numeric(df[mti_src], errors='coerce')
    t_mi_src = _resolve_rpt(df, 'Time_of_Max_Inflow') or _first_present(df, ['time_max_inflow', 't_tot_inflw'])
    if t_mi_src:
        out_cols['t_max_inf'] = df[t_mi_src]
    liv_src = _resolve_rpt(df, 'Lateral_Inflow_Volume') or _first_present(df, ['lat_inflow_vol'])
    if liv_src:
        out_cols['latinflvol'] = pd.to_numeric(df[liv_src], errors='coerce')
    tiv_src = _resolve_rpt(df, 'Total_Inflow_Volume') or _first_present(df, ['tot_inflow_vol'])
    if tiv_src:
        out_cols['totinflvol'] = pd.to_numeric(df[tiv_src], errors='coerce')

    # Note: Outfalls do not appear in Surcharge/Flooding summaries; omit those fields entirely

    # Column ordering: INP Outfalls (as in SWMM.inp) first, then RPT sections
    # in the order they appear in typical SWMM reports used by our extractor
    # (Node Summary -> Depth -> Inflow -> Surcharge -> Flooding -> Outfall Loading).
    # This preserves user-expected field ordering in attribute tables.
    #
    # INP [OUTFALLS]: Name, Invert_Elevation, Outfall_Type, Stage_Data, Tide_Gate
    # RPT Node Summary: inv_elev, max_depth, pond_area, ext_inflow
    # RPT Node Depth Summary: Avg_Depth, Max_Depth, Max_HGL, Time_of_Max_Depth
    # RPT Node Inflow Summary: Max_Lateral_Inflow, Max_Total_Inflow, Time_of_Max_Inflow, Lateral_Inflow_Volume, Total_Inflow_Volume
    # RPT Surcharge/Flooding Summaries
    # RPT Outfall Loading Summary: Flow_Freq_Pcnt, Avg_Flow_CFS, Max_Flow_CFS, Total_Volume_MG
    ordered = [
        # INP Outfalls (section order)
        'name', 'z_inv', 'o_type', 'stage', 'tide_gate',
        # RPT Node Summary
        'dmax_cap', 'pond_area', 'ext_in',
        # RPT Node Depth Summary
        'avg_dep', 'dmax_obs', 'max_hgl', 't_max_dep',
        # RPT Node Inflow Summary
        'lat_inflw', 'tot_inflw', 't_max_inf', 'latinflvol', 'totinflvol',
        # RPT Outfall Loading Summary (placed after other node-based summaries)
        'flwfrqpcnt', 'avg_flow', 'max_flow', 'tot_vol_mg',
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

"""Model data extraction coordinator for FLO-2D files.

This module orchestrates the extraction and merging of data from multiple
FLO-2D input and output files into a unified DataFrame for processing.
"""

import logging
import multiprocessing
import os
import time
from typing import Dict, Tuple, Union, Optional, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from extraction.base.extraction_utils import (
    log_time,
    ensure_unique_columns,
    verify_grid_ids,
    controlled_merge,
)
from core.file_discovery import get_file_path, check_file_exists
from core.constants import GRID_ID, NODE, normalize_grid_id
from extraction.out.depth_out_extraction import extract_depth_out
from extraction.dat.mannings_n_dat_extraction import extract_mannings_n_dat
from extraction.dat.topo_dat_extraction import extract_topo_dat
from extraction.out.velfp_out_extraction import extract_velfp_out
from extraction.out.maxqhyd_out_extraction import extract_maxqhyd_out
from extraction.out.maxwselev_out_extraction import extract_maxwselev_out
from extraction.out.infil_depth_out_extraction import extract_infil_depth_out
from extraction.out.timeoneft_out_extraction import extract_timeoneft_out
from extraction.out.timetwoft_out_extraction import extract_timetwoft_out
from extraction.out.timetopeak_out_extraction import extract_timetopeak_out
from extraction.out.finalvel_out_extraction import extract_finalvel_out
from extraction.out.finaldep_out_extraction import extract_finaldep_out
from extraction.dat.rain_dat_extraction import extract_rain_dat
from extraction.out.super_out_extraction import extract_super_out
from extraction.dat.infil_dat_extraction import extract_infil_dat, get_primary_infiltration_data
from extraction.dat.fpxsec_dat_extraction import extract_fpxsec_dat
from extraction.dat.arf_dat_extraction import extract_arf_dat
from extraction.out.veloc_out_extraction import extract_veloc_out
from extraction.out.depch_out_extraction import extract_depch_out
from extraction.out.time_out_extraction import extract_time_out
from extraction.out.evacuatedfp_out_extraction import extract_evacuatedfp_out
from extraction.out.outnq_out_extraction import extract_outnq_out, extract_outnq_summary
from extraction.dat.outflow_dat_extraction import extract_outflow_dat
from extraction.out.chanmax_out_extraction import extract_chanmax_out
from extraction.out.channel_extraction import extract_channel_data


## Removed ad-hoc normalization/rename adapters:
## - EVACUATEDFP, OUTNQ summary, OUTFLOW, and CHANMAX extractors now normalize/shape at source.


def _adapter_infil_primary(path: str) -> pd.DataFrame:
    """Adapter for INFIL.DAT to return the primary spatial infiltration dataset keyed by GRID_ID."""
    try:
        infil_data = extract_infil_dat(path)
        df = get_primary_infiltration_data(infil_data)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


FILE_EXTRACTORS = {
    # NOTE: Replaced by EXTRACTOR_REGISTRY below
}

# P2: Replace simple dict with a registry and profile support
# merge_key: 'GRID_ID' means regular merge; 'NONE' means ancillary/no merge into main
EXTRACTOR_REGISTRY: Dict[str, Dict[str, object]] = {
    # Core/grid-mergeable, lightweight
    'DEPTH.OUT':        { 'func': extract_depth_out,        'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'MANNINGS_N.DAT':   { 'func': extract_mannings_n_dat,   'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'TOPO.DAT':         { 'func': extract_topo_dat,         'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'VELFP.OUT':        { 'func': extract_velfp_out,        'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'MAXQHYD.OUT':      { 'func': extract_maxqhyd_out,      'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'MAXWSELEV.OUT':    { 'func': extract_maxwselev_out,    'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'INFIL_DEPTH.OUT':  { 'func': extract_infil_depth_out,  'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'TIMEONEFT.OUT':    { 'func': extract_timeoneft_out,    'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'TIMETWOFT.OUT':    { 'func': extract_timetwoft_out,    'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'TIMETOPEAK.OUT':   { 'func': extract_timetopeak_out,   'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'FINALVEL.OUT':     { 'func': extract_finalvel_out,     'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'FINALDEP.OUT':     { 'func': extract_finaldep_out,     'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'RAIN.DAT':         { 'func': extract_rain_dat,         'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'SUPER.OUT':        { 'func': extract_super_out,        'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'ARF.DAT':          { 'func': extract_arf_dat,          'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    # Added pool-wrapped special cases
    'INFIL.DAT':        { 'func': _adapter_infil_primary,   'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'FPXSEC.DAT':       { 'func': extract_fpxsec_dat,       'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    # P0 quick wins
    'VELOC.OUT':        { 'func': extract_veloc_out,        'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'DEPCH.OUT':        { 'func': extract_depch_out,        'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'TIME.OUT':         { 'func': extract_time_out,         'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'EVACUATEDFP.OUT':  { 'func': extract_evacuatedfp_out,  'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'OUTNQ.OUT':        { 'func': extract_outnq_summary,    'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'OUTFLOW.DAT':      { 'func': extract_outflow_dat,      'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    'CHANMAX.OUT':      { 'func': extract_chanmax_out,      'enabled': True,  'heavy': False, 'merge_key': 'GRID_ID' },
    # Virtual/optional heavy module
    'CHANNEL_COMBINED': { 'func': extract_channel_data,     'enabled': False, 'heavy': True,  'merge_key': 'GRID_ID', 'virtual': True, 'depends_on': ['CHAN.DAT'] },
}


def _resolve_enabled_extractors(
    performance_profile: str,
    enable: Optional[Iterable[str]] = None,
    disable: Optional[Iterable[str]] = None,
    enable_channel_combined: bool = False,
) -> Dict[str, Dict[str, object]]:
    """Return a filtered registry based on profile and explicit enables/disables."""
    profile = (performance_profile or 'fast').lower()

    # Start from default enabled flags
    registry = {name: meta.copy() for name, meta in EXTRACTOR_REGISTRY.items()}

    if profile == 'fast':
        # Disable heavy extractors by default
        for name, meta in registry.items():
            if meta.get('heavy'):
                meta['enabled'] = False
    elif profile == 'full':
        for meta in registry.values():
            meta['enabled'] = True
    elif profile == 'custom':
        # Keep defaults, will apply enable/disable below
        pass
    else:
        # Unknown -> treat as fast
        for name, meta in registry.items():
            if meta.get('heavy'):
                meta['enabled'] = False

    # Back-compat explicit channel flag
    if enable_channel_combined:
        registry['CHANNEL_COMBINED']['enabled'] = True
        # Avoid double work with standalone VELOC/DEPCH when combined on
        registry['VELOC.OUT']['enabled'] = False
        registry['DEPCH.OUT']['enabled'] = False

    # Apply explicit enables/disables
    if enable:
        for name in enable:
            if name in registry:
                registry[name]['enabled'] = True
    if disable:
        for name in disable:
            if name in registry:
                registry[name]['enabled'] = False

    # If CHANNEL_COMBINED is enabled, ensure its dependencies (files) are checked later
    return {name: meta for name, meta in registry.items() if meta.get('enabled')}


def extract_model_data_to_df(
    file_path: str,
    enable_channel_combined: bool = False,
    return_ancillary: bool = False,
    performance_profile: str = 'fast',
    enable: Optional[Iterable[str]] = None,
    disable: Optional[Iterable[str]] = None,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]]:
    """
    Extract and merge data from all available FLO-2D files into a unified DataFrame.
    
    Args:
        file_path (str): Path to the directory containing FLO-2D files.
        
    Returns:
        pd.DataFrame: Merged DataFrame containing all extracted data.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    logger.info("Starting model data extraction")
    start_time = time.time()

    data_frames: Dict[str, pd.DataFrame] = {}
    ancillary: Dict[str, pd.DataFrame] = {}

    # Determine enabled extractors per profile and flags
    enabled_registry = _resolve_enabled_extractors(
        performance_profile=performance_profile,
        enable=enable,
        disable=disable,
        enable_channel_combined=enable_channel_combined,
    )

    # Pre-scan for present files and cap workers accordingly
    present_extractors = []
    for name, meta in enabled_registry.items():
        # Virtual entries resolve via dependency presence, non-virtual check file
        if meta.get('virtual'):
            depends = meta.get('depends_on') or []
            # All required files must be present
            if all(check_file_exists(get_file_path(file_path, dep)) for dep in depends):
                present_extractors.append((name, meta['func']))
            else:
                logger.debug(f"Skipping {name}: missing dependencies {depends}")
        else:
            candidate_path = get_file_path(file_path, name)
            if check_file_exists(candidate_path):
                present_extractors.append((name, meta['func']))
            else:
                logger.debug(f"Skipping {name}: file not present")

    if not present_extractors:
        logger.warning("No extractable files found during pre-scan.")
    max_workers = max(1, min(multiprocessing.cpu_count() or 1, len(present_extractors) or 1))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, file_path): name for name, func in present_extractors}
        for future in as_completed(futures):
            name = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    data_frames[name] = df
                    logger.info(f"Processed {name}: {len(df)} rows")
                else:
                    logger.info(f"{name} is empty or returned no rows")
            except Exception as e:
                logger.error(f"Error processing {name}: {e}")

    # Fallback: if INFIL primary not already added by pool but INFIL.DAT exists
    infil_file = get_file_path(file_path, 'INFIL.DAT')
    if 'INFIL.DAT' not in data_frames and check_file_exists(infil_file):
        infil_data = extract_infil_dat(file_path)
        data_frames['INFIL.DAT'] = get_primary_infiltration_data(infil_data)

    # Fallback: if FPXSEC not already added by pool
    if 'FPXSEC.DAT' not in data_frames:
        fpxsec_df = extract_fpxsec_dat(file_path)
        if not fpxsec_df.empty:
            data_frames['FPXSEC.DAT'] = fpxsec_df

    # Ancillary: OUTNQ time series kept out of main merge
    try:
        outnq_path = get_file_path(file_path, 'OUTNQ.OUT')
        if check_file_exists(outnq_path):
            outnq = extract_outnq_out(file_path)
            ts = outnq.get('time_series') if isinstance(outnq, dict) else None
            if ts is not None:
                ancillary['outnq_time_series'] = ts
    except Exception:
        pass

    verify_grid_ids(data_frames)

    main_df = data_frames['DEPTH.OUT']
    logger.info(f"Main dataframe (DEPTH.OUT) shape: {main_df.shape}")

    merge_frames = {
        name: df for name, df in data_frames.items()
        if name != 'ARF.DAT'
    }
    main_df = controlled_merge(main_df, merge_frames)

    # Merge ARF data if available
    if 'ARF.DAT' in data_frames:
        from core.constants import GRID_ID, AREA_REDUCTION_FACTOR
        logger.info("Merging ARF.DAT data...")
        main_df = pd.merge(main_df, data_frames['ARF.DAT'], on=GRID_ID, how='left')
        main_df[AREA_REDUCTION_FACTOR] = main_df[AREA_REDUCTION_FACTOR].fillna(0.0)
        logger.info(f"Dataframe shape after merging ARF.DAT: {main_df.shape}")

    if 'SUPER.OUT' in data_frames:
        from core.constants import GRID_ID
        logger.info("Merging SUPER.OUT data...")
        main_df = pd.merge(main_df, data_frames['SUPER.OUT'], on=GRID_ID, how='left')
        logger.info(f"Dataframe shape after merging SUPER.OUT: {main_df.shape}")

    main_df = ensure_unique_columns(main_df)
    log_time("Extracting model data", start_time)
    if return_ancillary:
        return main_df, ancillary
    return main_df

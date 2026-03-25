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
from core.supported_files import (
    get_model_extractor_registry,
    get_required_model_files,
)
from extraction.dat.infil_dat_extraction import extract_infil_dat, get_primary_infiltration_data
from extraction.dat.fpxsec_dat_extraction import extract_fpxsec_dat
from extraction.out.outnq_out_extraction import extract_outnq_out


EXTRACTOR_REGISTRY: Dict[str, Dict[str, object]] = get_model_extractor_registry()
REQUIRED_MODEL_FILES = get_required_model_files()

REQUIRED_MODEL_FILES = ('DEPTH.OUT',)


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


def _validate_required_model_files(file_path: str) -> None:
    """Raise a clear error when required files for merged extraction are absent."""
    missing_files = [
        name for name in REQUIRED_MODEL_FILES
        if not check_file_exists(get_file_path(file_path, name))
    ]
    if missing_files:
        missing_text = ", ".join(missing_files)
        raise FileNotFoundError(
            f"Missing required FLO-2D file(s) for merged extraction in {file_path}: {missing_text}"
        )


def _validate_required_extractors(enabled_registry: Dict[str, Dict[str, object]]) -> None:
    """Reject configurations that disable required merged-model extractors."""
    disabled_required = [
        name for name in REQUIRED_MODEL_FILES
        if name not in enabled_registry
    ]
    if disabled_required:
        disabled_text = ", ".join(disabled_required)
        raise ValueError(
            f"Cannot disable required FLO-2D extractor(s) for merged extraction: {disabled_text}"
        )


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
    _validate_required_model_files(file_path)
    _validate_required_extractors(enabled_registry)

    # Pre-scan for present files and cap workers accordingly
    present_extractors = []
    extraction_errors: Dict[str, Exception] = {}
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
                extraction_errors[name] = e
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

    main_df = data_frames.get('DEPTH.OUT')
    if main_df is None or main_df.empty:
        depth_error = extraction_errors.get('DEPTH.OUT')
        if depth_error is not None:
            raise RuntimeError("Failed to extract required FLO-2D file DEPTH.OUT") from depth_error
        raise RuntimeError(
            f"Required FLO-2D file DEPTH.OUT did not produce any rows in {file_path}"
        )
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

    main_df = ensure_unique_columns(main_df)
    log_time("Extracting model data", start_time)
    if return_ancillary:
        return main_df, ancillary
    return main_df

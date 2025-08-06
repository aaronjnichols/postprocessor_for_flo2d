"""Model data extraction coordinator for FLO-2D files.

This module orchestrates the extraction and merging of data from multiple
FLO-2D input and output files into a unified DataFrame for processing.
"""

import logging
import multiprocessing
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from extraction.base.extraction_utils import (
    log_time,
    ensure_unique_columns,
    verify_grid_ids,
    controlled_merge,
)
from core.file_discovery import get_file_path, check_file_exists
from extraction.out.depth_out_extraction import extract_depth_out
from extraction.dat.mannings_n_dat_extraction import extract_mannings_n
from extraction.dat.topo_dat_extraction import extract_topo
from extraction.out.velfp_out_extraction import extract_velfp_out
from extraction.out.maxqhyd_out_extraction import extract_maxqhyd_out
from extraction.out.maxwselev_out_extraction import extract_maxwselev_out
from extraction.out.infil_depth_out_extraction import extract_infil_depth_out
from extraction.out.timeoneft_out_extraction import extract_timeoneft_out
from extraction.out.timetwoft_out_extraction import extract_timetwoft_out
from extraction.out.timetopeak_out_extraction import extract_timetopeak_out
from extraction.out.finalvel_out_extraction import extract_finalvel_out
from extraction.out.finaldep_out_extraction import extract_finaldep_out
from extraction.dat.rain_dat_extraction import extract_rain_data
from extraction.out.super_out_extraction import extract_super_out
from extraction.dat.infil_dat_extraction import extract_infil_dat
from extraction.dat.fpxsec_dat_extraction import extract_fpxsec_dat
from extraction.dat.arf_dat_extraction import extract_arf_dat


FILE_EXTRACTORS = {
    'DEPTH.OUT': extract_depth_out,
    'MANNINGS_N.DAT': extract_mannings_n,
    'TOPO.DAT': extract_topo,
    'VELFP.OUT': extract_velfp_out,
    'MAXQHYD.OUT': extract_maxqhyd_out,
    'MAXWSELEV.OUT': extract_maxwselev_out,
    'INFIL_DEPTH.OUT': extract_infil_depth_out,
    'TIMEONEFT.OUT': extract_timeoneft_out,
    'TIMETWOFT.OUT': extract_timetwoft_out,
    'TIMETOPEAK.OUT': extract_timetopeak_out,
    'FINALVEL.OUT': extract_finalvel_out,
    'FINALDEP.OUT': extract_finaldep_out,
    'RAIN.DAT': extract_rain_data,
    'SUPER.OUT': extract_super_out,
    'ARF.DAT': extract_arf_dat,
}


def extract_model_data_to_df(file_path: str) -> pd.DataFrame:
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

    data_frames = {}
    max_workers = multiprocessing.cpu_count() or 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(func, file_path): name
            for name, func in FILE_EXTRACTORS.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    data_frames[name] = df
                    logger.info(f"Processed {name}: {len(df)} rows")
                else:
                    logger.warning(f"{name} is empty or None")
            except Exception as e:
                logger.error(f"Error processing {name}: {e}")

    infil_file = get_file_path(file_path, 'INFIL.DAT')
    if check_file_exists(infil_file):
        data_frames['INFIL.DAT'] = extract_infil_dat(file_path)

    fpxsec_df = extract_fpxsec_dat(file_path)
    if not fpxsec_df.empty:
        data_frames['FPXSEC.DAT'] = fpxsec_df

    verify_grid_ids(data_frames)

    main_df = data_frames['DEPTH.OUT']
    logger.info(f"Main dataframe (DEPTH.OUT) shape: {main_df.shape}")

    main_df = controlled_merge(main_df, data_frames)

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
    return main_df

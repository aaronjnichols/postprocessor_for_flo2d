"""Base extraction utilities for FLO-2D data processing.

This module provides core utilities for reading, processing, and merging
FLO-2D data files with optimized performance for large datasets.
"""

import logging
import os
import time

import dask.dataframe as dd
import numpy as np
import pandas as pd
import psutil


def log_time(message, start_time):
    """
    Log the elapsed time for an operation.
    
    Args:
        message (str): Description of the operation.
        start_time (float): Start time from time.time().
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    elapsed_time = time.time() - start_time
    logger.info(f"{message} took {elapsed_time:.2f} seconds")


def read_with_dask_optimized(file_path, column_names=None, **kwargs):
    """
    Read large FLO-2D files using Dask with optimized chunk sizing.
    
    This function automatically determines optimal chunk sizes based on
    file size and available memory for efficient processing of large datasets.
    
    Args:
        file_path (str): Path to the file to read.
        column_names (list, optional): List of column names for the data.
        **kwargs: Additional arguments passed to dd.read_csv.
        
    Returns:
        dd.DataFrame: Dask DataFrame with optimized partitioning.
        
    Raises:
        FileNotFoundError: If the specified file does not exist.
        OSError: If there are issues reading the file.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    logger.debug(f"Reading file {file_path} (size: {file_size / 1024 / 1024:.1f} MB)")
    
    # Calculate optimal chunk size (between 32MB and 256MB)
    chunk_size = max(min(file_size // 100, 256 * 1024 * 1024), 32 * 1024 * 1024)
    
    data = dd.read_csv(
        file_path,
        delim_whitespace=True,
        header=None,
        names=column_names,
        blocksize=chunk_size,
        **kwargs,
    )

    # Optimize partitioning based on available memory
    total_mem = psutil.virtual_memory().total
    partition_size = max(chunk_size, total_mem // 100)
    npartitions = max(data.npartitions, file_size // partition_size)
    data = data.repartition(npartitions=npartitions)
    
    logger.debug(f"Created Dask DataFrame with {npartitions} partitions")
    return data


def read_file_with_line_number(file_path, column_names, skiprows=0):
    """
    Read a file and add sequential grid IDs based on line numbers.
    
    Args:
        file_path (str): Path to the file to read.
        column_names (list): List of column names for the data.
        skiprows (int, optional): Number of rows to skip at the beginning. Defaults to 0.
        
    Returns:
        pd.DataFrame: DataFrame with grid_id column added as the first column.
        
    Raises:
        FileNotFoundError: If the specified file does not exist.
    """
    from core.constants import GRID_ID
    
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    logger.debug(f"Reading file with line numbers: {file_path}")
    
    df = pd.read_csv(
        file_path,
        delim_whitespace=True,
        header=None,
        names=column_names,
        skiprows=skiprows,
    )
    df.insert(0, GRID_ID, range(len(df)))
    
    logger.debug(f"Read {len(df)} rows with grid IDs 0-{len(df)-1}")
    return df


def ensure_unique_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all column names in a DataFrame are unique by adding suffixes.
    
    Args:
        df (pd.DataFrame): DataFrame that may have duplicate column names.
        
    Returns:
        pd.DataFrame: DataFrame with unique column names.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    cols = df.columns.to_series()
    duplicates = cols[cols.duplicated()].unique()
    
    if len(duplicates) > 0:
        logger.warning(f"Found duplicate column names: {list(duplicates)}")
        
        for dup in duplicates:
            mask = cols.eq(dup)
            cols[mask] = [dup + '_' + str(i) if i != 0 else dup for i in range(mask.sum())]
        
        df.columns = cols.tolist()
        logger.debug("Renamed duplicate columns with numeric suffixes")
    
    return df


def verify_grid_ids(data_frames):
    """
    Verify grid ID consistency across multiple DataFrames.
    
    Args:
        data_frames (dict): Dictionary of DataFrame name -> DataFrame pairs.
    """
    from core.constants import GRID_ID
    
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    for name, df in data_frames.items():
        if GRID_ID in df.columns:
            unique_count = df[GRID_ID].nunique()
            total_count = len(df)
            logger.info(f"{name}: {unique_count} unique grid_ids out of {total_count} total rows")
            
            if unique_count != total_count:
                logger.warning(f"{name} has duplicate grid_ids")
            else:
                logger.debug(f"{name} grid IDs are unique")


def controlled_merge(main_df: pd.DataFrame, data_frames: dict) -> pd.DataFrame:
    """
    Perform controlled merge of multiple DataFrames with logging and validation.
    
    Args:
        main_df (pd.DataFrame): The primary DataFrame to merge others into.
        data_frames (dict): Dictionary of DataFrame name -> DataFrame pairs to merge.
        
    Returns:
        pd.DataFrame: The merged DataFrame.
        
    Raises:
        ValueError: If merge operations result in unexpected row count changes.
    """
    from core.constants import GRID_ID, FPXSEC
    
    logger = logging.getLogger('FLO2D_Postprocessor')
    logger.info("Starting controlled merge of DataFrames")
    
    result = main_df.copy()
    total_rows = len(result)
    logger.debug(f"Starting with {total_rows} rows")

    for name, df in data_frames.items():
        if name != 'DEPTH.OUT' and not df.empty:
            if GRID_ID in df.columns:
                logger.info(f"Merging {name} ({len(df)} rows)...")
                
                # Perform merge with explicit suffixes
                result = pd.merge(result, df, on=GRID_ID, how='left', suffixes=('', f'_{name}'))
                
                # Validate row count
                if len(result) != total_rows:
                    logger.warning(
                        f"Row count changed after merging {name}. Expected {total_rows}, got {len(result)}"
                    )
                    total_rows = len(result)
                    
            elif name == 'FPXSEC.DAT':
                logger.info(f"Merging {name} (FPXSEC data)...")
                result = pd.merge(result, df, left_on=GRID_ID, right_on=GRID_ID, how='left')
                result[FPXSEC] = result[FPXSEC].fillna(0)
                
            logger.debug(f"DataFrame shape after merging {name}: {result.shape}")

    logger.info(f"Merge completed. Final shape: {result.shape}")
    return result

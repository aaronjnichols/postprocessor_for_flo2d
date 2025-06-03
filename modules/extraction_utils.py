import os
import time
import psutil
import pandas as pd
import numpy as np
import dask.dataframe as dd


def log_time(message, start_time):
    elapsed_time = time.time() - start_time
    print(f"{message} took {elapsed_time:.2f} seconds")


def read_with_dask_optimized(file_path, column_names=None, **kwargs):
    file_size = os.path.getsize(file_path)
    chunk_size = max(min(file_size // 100, 256 * 1024 * 1024), 32 * 1024 * 1024)
    data = dd.read_csv(
        file_path,
        delim_whitespace=True,
        header=None,
        names=column_names,
        blocksize=chunk_size,
        **kwargs,
    )

    total_mem = psutil.virtual_memory().total
    partition_size = max(chunk_size, total_mem // 100)
    npartitions = max(data.npartitions, file_size // partition_size)
    data = data.repartition(npartitions=npartitions)
    return data


def read_file_with_line_number(file_path, column_names, skiprows=0):
    df = pd.read_csv(
        file_path,
        delim_whitespace=True,
        header=None,
        names=column_names,
        skiprows=skiprows,
    )
    df.insert(0, 'grid_id', range(len(df)))
    return df


def ensure_unique_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = df.columns.to_series()
    for dup in cols[cols.duplicated()].unique():
        mask = cols.eq(dup)
        cols[mask] = [dup + '_' + str(i) if i != 0 else dup for i in range(mask.sum())]
    df.columns = cols.tolist()
    return df


def verify_grid_ids(data_frames):
    for name, df in data_frames.items():
        if 'grid_id' in df.columns:
            unique_count = df['grid_id'].nunique()
            total_count = len(df)
            print(f"{name}: {unique_count} unique grid_ids out of {total_count} total rows")
            if unique_count != total_count:
                print(f"Warning: {name} has duplicate grid_ids")


def controlled_merge(main_df: pd.DataFrame, data_frames: dict) -> pd.DataFrame:
    print("Starting controlled merge...")
    result = main_df.copy()
    total_rows = len(result)

    for name, df in data_frames.items():
        if name != 'DEPTH.OUT' and not df.empty:
            if 'grid_id' in df.columns:
                print(f"Merging {name}...")
                result = pd.merge(result, df, on='grid_id', how='left', suffixes=('', f'_{name}'))
                if len(result) != total_rows:
                    print(
                        f"Warning: Row count changed after merging {name}. Expected {total_rows}, got {len(result)}"
                    )
                    total_rows = len(result)
            elif name == 'FPXSEC.DAT':
                print(f"Merging {name}...")
                result = pd.merge(result, df, left_on='grid_id', right_on='grid_id', how='left')
                result['fpxsec'] = result['fpxsec'].fillna(0)
        print(f"Current dataframe shape after merging {name}: {result.shape}")

    print("Merge complete.")
    return result

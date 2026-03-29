import os
import logging
import pandas as pd
from core.constants import OUTFLOW_CODE, GRID_ID, normalize_grid_id
from core.logger import setup_logger
from core.path_resolver import resolve_model_file_path

def extract_outflow_dat(folder_path):
    """
    Extract outflow grid cell data from OUTFLOW.DAT file.
    
    Args:
        folder_path (str): Path to the directory containing OUTFLOW.DAT file.
        
    Returns:
        pd.DataFrame: DataFrame with columns ['outflow_code', 'grid_id'] containing
                     outflow boundary data. Returns empty DataFrame on error.
                     
    Raises:
        FileNotFoundError: If OUTFLOW.DAT file is not found.
    """
    logger = setup_logger('OUTFLOW_DAT', level=logging.INFO)
    file_path = resolve_model_file_path(folder_path, 'OUTFLOW.DAT')
    
    if not os.path.exists(file_path):
        logger.error(f"OUTFLOW.DAT file not found at {file_path}")
        raise FileNotFoundError(f"OUTFLOW.DAT file not found at {file_path}")
    
    try:
        rows = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                parts = line.split()
                if len(parts) < 2:
                    continue
                outflow_code, grid_id = parts[0], parts[1]
                if not outflow_code.startswith("O"):
                    continue
                rows.append({OUTFLOW_CODE: outflow_code, GRID_ID: grid_id})

        if not rows:
            logger.warning(f"No data found in {file_path}")
            return pd.DataFrame(columns=[OUTFLOW_CODE, GRID_ID])

        outflow_df = pd.DataFrame(rows, columns=[OUTFLOW_CODE, GRID_ID])
        
        # Normalize grid ids to internal 0-based Int64
        if not outflow_df.empty:
            outflow_df[GRID_ID] = pd.to_numeric(outflow_df[GRID_ID], errors='coerce').astype('Int64')
            outflow_df = outflow_df.dropna(subset=[GRID_ID]).copy()
            outflow_df[GRID_ID] = outflow_df[GRID_ID].apply(
                lambda v: normalize_grid_id(int(v)) if pd.notna(v) else v
            )

        logger.info(f"Successfully extracted {len(outflow_df)} outflow records from OUTFLOW.DAT")
        return outflow_df
        
    except IOError as e:
        logger.error(f"Error reading OUTFLOW.DAT file: {e}")
        return pd.DataFrame(columns=[OUTFLOW_CODE, GRID_ID])
    except Exception as e:
        logger.error(f"Unexpected error processing OUTFLOW.DAT file: {e}", exc_info=True)
        return pd.DataFrame(columns=[OUTFLOW_CODE, GRID_ID]) 

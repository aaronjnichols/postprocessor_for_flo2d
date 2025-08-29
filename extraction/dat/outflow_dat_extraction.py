import os
import logging
import pandas as pd
from core.constants import OUTFLOW_CODE, GRID_ID, normalize_grid_id
from core.logger import setup_logger

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
    file_path = os.path.join(folder_path, 'OUTFLOW.DAT')
    
    if not os.path.exists(file_path):
        logger.error(f"OUTFLOW.DAT file not found at {file_path}")
        raise FileNotFoundError(f"OUTFLOW.DAT file not found at {file_path}")
    
    try:
        # Read the file with whitespace delimiter
        df = pd.read_csv(
            file_path,
            sep=r'\s+',
            header=None,
            names=[OUTFLOW_CODE, GRID_ID],
            dtype={OUTFLOW_CODE: str, GRID_ID: str}
        )
        
        if df.empty:
            logger.warning(f"No data found in {file_path}")
            return pd.DataFrame(columns=[OUTFLOW_CODE, GRID_ID])
        
        # Filter to only outflow records (lines starting with 'O')
        outflow_df = df[df[OUTFLOW_CODE].str.startswith('O', na=False)].copy()
        
        if outflow_df.empty:
            logger.warning(f"No outflow records found in {file_path}")
            return pd.DataFrame(columns=[OUTFLOW_CODE, GRID_ID])
        
        # Normalize grid ids to internal 0-based Int64
        if not outflow_df.empty:
            outflow_df[GRID_ID] = pd.to_numeric(outflow_df[GRID_ID], errors='coerce').astype('Int64')
            outflow_df[GRID_ID] = outflow_df[GRID_ID].apply(
                lambda v: normalize_grid_id(int(v)) if pd.notna(v) else v
            )

        logger.info(f"Successfully extracted {len(outflow_df)} outflow records from OUTFLOW.DAT")
        return outflow_df
        
    except pd.errors.EmptyDataError:
        logger.warning(f"OUTFLOW.DAT file is empty: {file_path}")
        return pd.DataFrame(columns=[OUTFLOW_CODE, GRID_ID])
    except IOError as e:
        logger.error(f"Error reading OUTFLOW.DAT file: {e}")
        return pd.DataFrame(columns=[OUTFLOW_CODE, GRID_ID])
    except Exception as e:
        logger.error(f"Unexpected error processing OUTFLOW.DAT file: {e}", exc_info=True)
        return pd.DataFrame(columns=[OUTFLOW_CODE, GRID_ID]) 

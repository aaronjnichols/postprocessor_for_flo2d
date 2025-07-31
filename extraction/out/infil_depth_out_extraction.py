import os
import logging
import pandas as pd
from core.constants import GRID_ID, X_COORD, Y_COORD, INFIL_DEPTH


def extract_infil_depth_out(path):
    """
    Extract infiltration depth data from INFIL_DEPTH.OUT file.
    
    INFIL_DEPTH.OUT format: X_COORD Y_COORD INFIL_DEPTH INFIL_STOP
    Grid IDs are generated sequentially to match the grid ordering.
    
    Args:
        path (str): Path to the directory containing INFIL_DEPTH.OUT file.
        
    Returns:
        pd.DataFrame: DataFrame with grid_id, x, y, infil_depth, and infil_stop columns.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    file_path = os.path.join(path, 'INFIL_DEPTH.OUT')
    
    if not os.path.exists(file_path):
        logger.warning(f"INFIL_DEPTH.OUT file not found at {file_path}")
        return pd.DataFrame(columns=[GRID_ID, X_COORD, Y_COORD, INFIL_DEPTH, 'infil_stop'])
    
    try:
        # Examine file structure first
        with open(file_path, 'r') as f:
            sample_lines = []
            for i, line in enumerate(f):
                if i >= 10:  # Read first 10 lines
                    break
                if line.strip():
                    sample_lines.append(line.strip())
        
        if not sample_lines:
            logger.warning(f"INFIL_DEPTH.OUT file appears to be empty: {file_path}")
            return pd.DataFrame(columns=[GRID_ID, X_COORD, Y_COORD, INFIL_DEPTH, 'infil_stop'])
        
        # Find where data starts (skip headers)
        skip_rows = 0
        for i, line in enumerate(sample_lines):
            parts = line.split()
            if len(parts) >= 3:  # Should have at least X, Y, depth
                try:
                    float(parts[0])  # X coordinate
                    float(parts[1])  # Y coordinate  
                    float(parts[2])  # Infiltration depth
                    skip_rows = i
                    break
                except ValueError:
                    continue
        
        logger.info(f"INFIL_DEPTH.OUT: Skipping {skip_rows} header lines")
        
        # Read the file - typically has format: X Y INFIL_DEPTH INFIL_STOP
        df = pd.read_csv(
            file_path,
            delim_whitespace=True,
            header=None,
            names=[X_COORD, Y_COORD, INFIL_DEPTH, 'infil_stop'],
            skiprows=skip_rows,
            dtype=float
        )
        
        # Generate sequential grid IDs starting from 0 to match grid ordering
        df.insert(0, GRID_ID, range(len(df)))
        
        logger.info(f"Successfully read INFIL_DEPTH.OUT: {len(df)} grid points")
        return df
        
    except Exception as e:
        logger.error(f"Error reading INFIL_DEPTH.OUT file: {e}")
        # Return empty DataFrame to prevent merge issues
        return pd.DataFrame(columns=[GRID_ID, X_COORD, Y_COORD, INFIL_DEPTH, 'infil_stop'])

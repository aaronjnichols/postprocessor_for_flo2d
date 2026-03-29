import os
import logging
import pandas as pd
from core.utilities import time_function
from core.constants import GRID_ID, X_COORD, Y_COORD, INFIL_DEPTH, INFIL_STOP
from core.path_resolver import resolve_model_file_path


@time_function
def extract_infil_depth_out(path):
    """
    Extract infiltration depth data from INFIL_DEPTH.OUT file.
    
    This function reads infiltration depth and termination data for each grid cell.
    File format: X_COORD Y_COORD INFIL_DEPTH INFIL_STOP
    Grid IDs are generated sequentially starting from 0 to match grid ordering.
    
    Args:
        path (str): Path to the directory containing INFIL_DEPTH.OUT file
        
    Returns:
        pd.DataFrame: DataFrame with columns [GRID_ID, X_COORD, Y_COORD, INFIL_DEPTH, INFIL_STOP]
        
    Raises:
        FileNotFoundError: If INFIL_DEPTH.OUT file is not found
        ValueError: If file is empty or contains no valid data
        RuntimeError: If error reading file
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    file_path = resolve_model_file_path(path, 'INFIL_DEPTH.OUT')
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"INFIL_DEPTH.OUT file not found at {file_path}")
    
    try:
        # Examine file structure to detect header lines
        with open(file_path, 'r') as file:
            sample_lines = []
            for line_num, line in enumerate(file):
                if line_num >= 10:  # Read first 10 lines to detect format
                    break
                if line.strip():
                    sample_lines.append(line.strip())
        
        if not sample_lines:
            raise ValueError(f"INFIL_DEPTH.OUT file appears to be empty: {file_path}")
        
        # Detect where numeric data starts (skip any header lines)
        data_start_row = 0
        for row_idx, line in enumerate(sample_lines):
            parts = line.split()
            if len(parts) >= 3:  # Should have at least X, Y, infiltration_depth
                try:
                    float(parts[0])  # X coordinate
                    float(parts[1])  # Y coordinate  
                    float(parts[2])  # Infiltration depth
                    data_start_row = row_idx
                    break
                except ValueError:
                    continue
        
        logger.info(f"INFIL_DEPTH.OUT: Skipping {data_start_row} header lines")
        
        # Read the file with expected format: X Y INFIL_DEPTH INFIL_STOP
        df = pd.read_csv(
            file_path,
            delim_whitespace=True,
            header=None,
            names=[X_COORD, Y_COORD, INFIL_DEPTH, INFIL_STOP],
            skiprows=data_start_row,
            dtype=float
        )
        
        # Generate sequential grid IDs starting from 0 to match grid ordering
        df.insert(0, GRID_ID, range(len(df)))
        
        logger.info(f"Successfully read INFIL_DEPTH.OUT: {len(df)} grid points")
        return df
        
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error reading INFIL_DEPTH.OUT file: {e}") from e

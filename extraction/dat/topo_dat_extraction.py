import os
import logging
import pandas as pd
from core.constants import GRID_ID, X_COORD, Y_COORD, TOPO_ELEVATION, normalize_grid_id


def extract_topo(path):
    """
    Extract topographic data from TOPO.DAT file.
    
    TOPO.DAT format: GRID_ID X_COORD Y_COORD TOPO_ELEVATION
    Grid IDs are 1-based in FLO-2D files and get normalized to 0-based.
    
    Args:
        path (str): Path to the directory containing TOPO.DAT file.
        
    Returns:
        pd.DataFrame: DataFrame with grid_id, x, y, and topo_elevation columns.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    file_path = os.path.join(path, 'TOPO.DAT')
    
    if not os.path.exists(file_path):
        logger.warning(f"TOPO.DAT file not found at {file_path}")
        return pd.DataFrame(columns=[GRID_ID, X_COORD, Y_COORD, TOPO_ELEVATION])
    
    try:
        # First, examine the file structure to determine the correct format
        with open(file_path, 'r') as f:
            # Read first few lines to understand format
            sample_lines = []
            for i, line in enumerate(f):
                if i >= 10:  # Read first 10 lines max
                    break
                if line.strip():  # Skip empty lines
                    sample_lines.append(line.strip())
        
        if not sample_lines:
            logger.warning(f"TOPO.DAT file appears to be empty: {file_path}")
            return pd.DataFrame(columns=[GRID_ID, X_COORD, Y_COORD, TOPO_ELEVATION])
        
        # Analyze first non-empty line to determine format
        first_line = sample_lines[0]
        parts = first_line.split()
        logger.info(f"TOPO.DAT first line has {len(parts)} columns: {first_line}")
        
        # Determine if we need to skip header lines
        skip_rows = 0
        for i, line in enumerate(sample_lines):
            parts = line.split()
            if len(parts) >= 3:  # At least 3 columns expected
                try:
                    # Try to parse first three values as numbers
                    float(parts[0])
                    float(parts[1]) 
                    float(parts[2])
                    # If successful, this is likely the start of data
                    skip_rows = i
                    break
                except ValueError:
                    # This line doesn't contain numeric data, might be header
                    continue
        
        logger.info(f"Skipping {skip_rows} header lines in TOPO.DAT")
        
        # Read the file with proper handling
        if len(parts) == 3:
            # Format: X Y ELEVATION (no grid ID column)
            logger.info("TOPO.DAT format detected: X Y ELEVATION (generating sequential grid IDs)")
            df = pd.read_csv(
                file_path,
                delim_whitespace=True,
                header=None,
                names=[X_COORD, Y_COORD, TOPO_ELEVATION],
                skiprows=skip_rows,
                dtype=float
            )
            # Generate sequential grid IDs starting from 0
            df.insert(0, GRID_ID, range(len(df)))
            
        elif len(parts) == 4:
            # Format: GRID_ID X Y ELEVATION
            logger.info("TOPO.DAT format detected: GRID_ID X Y ELEVATION")
            df = pd.read_csv(
                file_path,
                delim_whitespace=True,
                header=None,
                names=[GRID_ID, X_COORD, Y_COORD, TOPO_ELEVATION],
                skiprows=skip_rows,
                dtype={GRID_ID: int, X_COORD: float, Y_COORD: float, TOPO_ELEVATION: float}
            )
            # Normalize grid IDs from 1-based to 0-based
            df[GRID_ID] = df[GRID_ID].apply(normalize_grid_id)
            
        else:
            logger.error(f"Unexpected TOPO.DAT format with {len(parts)} columns. Expected 3 or 4 columns.")
            # Fallback: try to read as 3 columns and generate grid IDs
            df = pd.read_csv(
                file_path,
                delim_whitespace=True,
                header=None,
                usecols=[0, 1, 2],  # Only use first 3 columns
                names=[X_COORD, Y_COORD, TOPO_ELEVATION],
                skiprows=skip_rows,
                dtype=float
            )
            df.insert(0, GRID_ID, range(len(df)))
        
        logger.info(f"Successfully read TOPO.DAT: {len(df)} grid points")
        logger.info(f"Grid ID range: {df[GRID_ID].min()} to {df[GRID_ID].max()}")
        logger.info(f"Coordinate ranges: X({df[X_COORD].min():.1f} to {df[X_COORD].max():.1f}), Y({df[Y_COORD].min():.1f} to {df[Y_COORD].max():.1f})")
        
        return df
        
    except Exception as e:
        logger.error(f"Error reading TOPO.DAT file: {e}")
        logger.info("Falling back to original method for TOPO.DAT extraction")
        
        # Fallback to the original line-based approach if all else fails
        try:
            from extraction.base.extraction_utils import read_file_with_line_number
            df = read_file_with_line_number(file_path, [X_COORD, Y_COORD, TOPO_ELEVATION])
            logger.warning("Using fallback method with sequential grid IDs - inflow positioning may be incorrect")
            return df
        except Exception as fallback_error:
            logger.error(f"Fallback method also failed: {fallback_error}")
            return pd.DataFrame(columns=[GRID_ID, X_COORD, Y_COORD, TOPO_ELEVATION])

"""
Module for extracting comprehensive channel data from FLO-2D CHAN.DAT files.

This module provides functions to parse and extract all types of channel data
from FLO-2D model files, including rectangular, trapezoidal, variable area, and
natural channels, as well as confluences and other channel-related data.
"""

# Standard library imports
import os
import logging
from typing import Dict, List, Any, Optional

# Third-party imports
import pandas as pd

# Local application imports
from core.utilities import time_function
from core.constants import GRID_ID
from core.logger import setup_logger


@time_function
def extract_chan_dat(path: str) -> Dict[str, pd.DataFrame]:
    """
    Extract comprehensive channel data from CHAN.DAT file.
    
    Args:
        path (str): Path to the directory containing CHAN.DAT file.
        
    Returns:
        Dict[str, pd.DataFrame]: Dictionary containing:
            - segments: Segment parameter data
            - channels: Channel element geometry data  
            - confluences: Channel confluence connections
            - no_exchange: Elements that don't exchange flow with floodplain
            - initial_ws: Initial water surface elevations
            
    Raises:
        FileNotFoundError: If CHAN.DAT file is not found.
        ValueError: If file contains invalid channel geometry data.
    """
    logger = setup_logger('CHAN_DAT', level=logging.INFO)
    file_path = os.path.join(path, 'CHAN.DAT')
    
    if not os.path.exists(file_path):
        logger.error(f"CHAN.DAT file not found at {file_path}")
        raise FileNotFoundError(f"CHAN.DAT file not found at {file_path}")
    
    segments = []
    channels = []
    confluences = []
    no_exchange = []
    initial_ws = []
    
    current_segment_id = 0
    
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except IOError as e:
        logger.error(f"Error reading CHAN.DAT file: {e}")
        raise IOError(f"Failed to read CHAN.DAT file: {e}")
    
    line_num = 0
    while line_num < len(lines):
        line = lines[line_num].strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            line_num += 1
            continue
            
        parts = line.split()
        if not parts:
            line_num += 1
            continue
        
        try:
            # Determine line type and process accordingly
            line_type = _classify_line(parts)
            
            if line_type == 'segment_header':
                segment_data = _parse_segment_header(parts, current_segment_id)
                segments.append(segment_data)
                current_segment_id += 1
                
            elif line_type == 'channel_element':
                channel_data = _parse_channel_element(parts, current_segment_id - 1)
                channels.append(channel_data)
                
            elif line_type == 'confluence':
                confluence_data = _parse_confluence(parts)
                confluences.append(confluence_data)
                
            elif line_type == 'no_exchange':
                no_exchange_grid = _parse_no_exchange(parts)
                no_exchange.append(no_exchange_grid)
                
            elif line_type == 'initial_ws':
                ws_data = _parse_initial_ws(parts)
                initial_ws.append(ws_data)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing line {line_num + 1}: {line.strip()}. Error: {e}")
            
        line_num += 1
    
    # Create DataFrames with proper handling of empty data
    result = {
        'segments': pd.DataFrame(segments) if segments else pd.DataFrame(),
        'channels': pd.DataFrame(channels) if channels else pd.DataFrame(),
        'confluences': pd.DataFrame(confluences) if confluences else pd.DataFrame(),
        'no_exchange': pd.DataFrame({GRID_ID: no_exchange}) if no_exchange else pd.DataFrame(),
        'initial_ws': pd.DataFrame(initial_ws) if initial_ws else pd.DataFrame()
    }
    
    logger.info(f"Successfully extracted channel data: "
               f"{len(segments)} segments, {len(channels)} channel elements, "
               f"{len(confluences)} confluences, {len(no_exchange)} no-exchange elements, "
               f"{len(initial_ws)} initial WS elements")
    
    return result


def _classify_line(parts: List[str]) -> str:
    """
    Classify the type of line in CHAN.DAT based on first element.
    
    Args:
        parts (List[str]): Split line parts.
        
    Returns:
        str: Line type classification.
    """
    if not parts:
        return 'empty'
    
    first_part = parts[0]
    
    # Channel element shapes
    if first_part in ['R', 'V', 'T', 'N']:
        return 'channel_element'
    
    # Confluence indicator
    if first_part == 'C':
        return 'confluence'
    
    # No exchange indicator  
    if first_part == 'E':
        return 'no_exchange'
    
    # Check if it's a number (could be segment header or initial WS)
    try:
        float(first_part)
        # Segment headers typically have 3-4 values
        if len(parts) >= 3:
            return 'segment_header'
        # Initial WS typically has 2 values (grid_id, elevation)
        elif len(parts) == 2:
            return 'initial_ws'
        else:
            return 'unknown'
    except ValueError:
        return 'unknown'


def _parse_segment_header(parts: List[str], segment_id: int) -> Dict[str, Any]:
    """
    Parse segment header line containing segment parameters.
    
    Args:
        parts (List[str]): Split line parts.
        segment_id (int): Current segment identifier.
        
    Returns:
        Dict[str, Any]: Parsed segment data.
    """
    return {
        'segment_id': segment_id,
        'depinitial': float(parts[0]),
        'froudc': float(parts[1]),
        'roughadj': float(parts[2]),
        'isedn': int(parts[3]) if len(parts) > 3 else None
    }


def _parse_channel_element(parts: List[str], segment_id: int) -> Dict[str, Any]:
    """
    Parse channel element line based on geometry type.
    
    Args:
        parts (List[str]): Split line parts.
        segment_id (int): Associated segment identifier.
        
    Returns:
        Dict[str, Any]: Parsed channel element data.
        
    Raises:
        ValueError: If unknown channel shape is encountered.
    """
    shape = parts[0]
    
    # Base data common to all channel types
    base_data = {
        'segment_id': segment_id,
        'shape': shape,
        GRID_ID: int(parts[1])
    }
    
    if shape == 'R':  # Rectangular channel
        return {**base_data, **_parse_rectangular(parts)}
    elif shape == 'V':  # Variable area channel
        return {**base_data, **_parse_variable(parts)}
    elif shape == 'T':  # Trapezoidal channel
        return {**base_data, **_parse_trapezoidal(parts)}
    elif shape == 'N':  # Natural channel
        return {**base_data, **_parse_natural(parts)}
    else:
        raise ValueError(f"Unknown channel shape: {shape}")


def _parse_rectangular(parts: List[str]) -> Dict[str, float]:
    """
    Parse rectangular channel geometry.
    Format: R GRID BANKELL BANKELR FCN FCW FCD XLEN
    
    Args:
        parts (List[str]): Split line parts.
        
    Returns:
        Dict[str, float]: Rectangular channel parameters.
    """
    return {
        'bank_left_elev': float(parts[2]),
        'bank_right_elev': float(parts[3]),
        'manning_n': float(parts[4]),
        'width': float(parts[5]),
        'depth': float(parts[6]),
        'length': float(parts[7])
    }


def _parse_variable(parts: List[str]) -> Dict[str, Optional[float]]:
    """
    Parse variable area channel geometry.
    Format: V GRID BANKELL BANKELR FCN FCD XLEN A1 A2 B1 B2 C1 C2 EXCDEP A11 A22 B11 B22 C11 C22
    
    Args:
        parts (List[str]): Split line parts.
        
    Returns:
        Dict[str, Optional[float]]: Variable area channel parameters.
    """
    return {
        'bank_left_elev': float(parts[2]),
        'bank_right_elev': float(parts[3]),
        'manning_n': float(parts[4]),
        'depth': float(parts[5]),
        'length': float(parts[6]),
        'area_coeff_1': float(parts[7]),
        'area_exp_1': float(parts[8]),
        'wetted_perim_coeff_1': float(parts[9]),
        'wetted_perim_exp_1': float(parts[10]),
        'top_width_coeff_1': float(parts[11]),
        'top_width_exp_1': float(parts[12]),
        'exceed_depth': float(parts[13]),
        'area_coeff_2': float(parts[14]) if len(parts) > 14 else None,
        'area_exp_2': float(parts[15]) if len(parts) > 15 else None,
        'wetted_perim_coeff_2': float(parts[16]) if len(parts) > 16 else None,
        'wetted_perim_exp_2': float(parts[17]) if len(parts) > 17 else None,
        'top_width_coeff_2': float(parts[18]) if len(parts) > 18 else None,
        'top_width_exp_2': float(parts[19]) if len(parts) > 19 else None
    }


def _parse_trapezoidal(parts: List[str]) -> Dict[str, float]:
    """
    Parse trapezoidal channel geometry.
    Format: T GRID BANKELL BANKELR FCN FCW FCD XLEN ZL ZR
    
    Args:
        parts (List[str]): Split line parts.
        
    Returns:
        Dict[str, float]: Trapezoidal channel parameters.
    """
    return {
        'bank_left_elev': float(parts[2]),
        'bank_right_elev': float(parts[3]),
        'manning_n': float(parts[4]),
        'bottom_width': float(parts[5]),
        'depth': float(parts[6]),
        'length': float(parts[7]),
        'left_side_slope': float(parts[8]),
        'right_side_slope': float(parts[9])
    }


def _parse_natural(parts: List[str]) -> Dict[str, Any]:
    """
    Parse natural channel geometry.
    Format: N GRID FCN XLEN NXSECNUM
    
    Args:
        parts (List[str]): Split line parts.
        
    Returns:
        Dict[str, Any]: Natural channel parameters.
    """
    return {
        'manning_n': float(parts[2]),
        'length': float(parts[3]),
        'xsec_number': int(parts[4])
    }


def _parse_confluence(parts: List[str]) -> Dict[str, int]:
    """
    Parse confluence connection line.
    Format: C TRIBUTARY_GRID MAIN_GRID
    
    Args:
        parts (List[str]): Split line parts.
        
    Returns:
        Dict[str, int]: Confluence connection data.
    """
    return {
        'tributary_grid': int(parts[1]),
        'main_channel_grid': int(parts[2])
    }


def _parse_no_exchange(parts: List[str]) -> int:
    """
    Parse no exchange element line.
    Format: E GRID
    
    Args:
        parts (List[str]): Split line parts.
        
    Returns:
        int: Grid ID that doesn't exchange flow with floodplain.
    """
    return int(parts[1])


def _parse_initial_ws(parts: List[str]) -> Dict[str, Any]:
    """
    Parse initial water surface elevation line.
    Format: GRID WS_ELEVATION
    
    Args:
        parts (List[str]): Split line parts.
        
    Returns:
        Dict[str, Any]: Initial water surface data.
    """
    return {
        GRID_ID: int(parts[0]),
        'initial_ws_elev': float(parts[1])
    }


@time_function  
def validate_chan_data(chan_data: Dict[str, pd.DataFrame]) -> List[str]:
    """
    Validate extracted channel data and return list of warnings/errors.
    
    Args:
        chan_data (Dict[str, pd.DataFrame]): Extracted channel data.
        
    Returns:
        List[str]: List of validation warnings and errors.
    """
    logger = setup_logger('CHAN_VALIDATION', level=logging.INFO)
    warnings = []
    
    channels_df = chan_data['channels']
    if not channels_df.empty:
        # Check for duplicate grid IDs
        duplicates = channels_df[channels_df[GRID_ID].duplicated()]
        if not duplicates.empty:
            warning_msg = f"Duplicate grid IDs found in channels: {duplicates[GRID_ID].tolist()}"
            warnings.append(warning_msg)
            logger.warning(warning_msg)
        
        # Check for missing Manning's n values
        missing_n = channels_df[channels_df['manning_n'].isna()]
        if not missing_n.empty:
            warning_msg = f"Missing Manning's n values for grids: {missing_n[GRID_ID].tolist()}"
            warnings.append(warning_msg)
            logger.warning(warning_msg)
        
        # Check for unrealistic Manning's n values
        bad_n = channels_df[(channels_df['manning_n'] < 0.01) | (channels_df['manning_n'] > 0.25)]
        if not bad_n.empty:
            warning_msg = f"Unusual Manning's n values (outside 0.01-0.25): {bad_n[GRID_ID].tolist()}"
            warnings.append(warning_msg)
            logger.warning(warning_msg)
    
    # Check confluence connectivity
    confluences_df = chan_data['confluences']
    if not confluences_df.empty and not channels_df.empty:
        channel_grids = set(channels_df[GRID_ID])
        for _, confluence in confluences_df.iterrows():
            if confluence['tributary_grid'] not in channel_grids:
                warning_msg = f"Confluence tributary {confluence['tributary_grid']} not in channel elements"
                warnings.append(warning_msg)
                logger.warning(warning_msg)
            if confluence['main_channel_grid'] not in channel_grids:
                warning_msg = f"Confluence main channel {confluence['main_channel_grid']} not in channel elements"
                warnings.append(warning_msg)
                logger.warning(warning_msg)
    
    if not warnings:
        logger.info("Channel data validation completed with no issues")
    
    return warnings
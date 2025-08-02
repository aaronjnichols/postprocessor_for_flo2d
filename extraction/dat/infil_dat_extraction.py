"""Module for extracting infiltration data from FLO-2D INFIL.DAT files.

This module provides comprehensive functions to parse and extract infiltration
data from FLO-2D model files, supporting all infiltration methods and data types.
"""

import os
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Union

from core.constants import (
    GRID_ID, XKSAT, PSIF, DTHETA, ABSTRINF, RTIMPF, SOIL_DEPTH,
    CURVE_NUMBER, CHANNEL_ELEMENT, HYDCON, REACH_ID, HYDCX_INITIAL, 
    HYDCX_FINAL, FHORTI, FHORTF, DECAY_COEFF
)
from core.logger import setup_logger

logger = setup_logger('infil_dat_extraction')


def extract_infil_dat(path: str) -> pd.DataFrame:
    """
    Extract Green-Ampt infiltration data from INFIL.DAT file (backward compatible).
    
    This function maintains backward compatibility by returning only the Green-Ampt
    spatial data (F lines) as a DataFrame, which matches the original behavior.
    
    Args:
        path (str): Path to the directory containing INFIL.DAT file.
        
    Returns:
        pd.DataFrame: DataFrame with Green-Ampt spatial data columns.
        
    Raises:
        FileNotFoundError: If INFIL.DAT file is not found.
        ValueError: If file format is invalid or no Green-Ampt data found.
    """
    try:
        comprehensive_data = extract_infil_dat_comprehensive(path)
        ga_data = comprehensive_data['green_ampt_spatial']
        
        if ga_data.empty:
            logger.warning("No Green-Ampt spatial data found in INFIL.DAT")
            columns = [GRID_ID, XKSAT, PSIF, DTHETA, ABSTRINF, RTIMPF, SOIL_DEPTH]
            return pd.DataFrame(columns=columns)
            
        return ga_data
        
    except Exception as e:
        logger.error(f"Failed to extract infiltration data from {path}: {e}")
        raise


def extract_infil_dat_comprehensive(path: str) -> Dict[str, Union[pd.DataFrame, Dict[str, Any]]]:
    """
    Extract comprehensive infiltration data from INFIL.DAT file.
    
    Returns dictionary containing all infiltration data types including method
    information, global parameters, and spatial data for all supported methods.
    
    Args:
        path (str): Path to the directory containing INFIL.DAT file.
        
    Returns:
        Dict containing:
        - method_info: Infiltration method and global parameters
        - green_ampt_global: Global Green-Ampt parameters (if applicable)
        - green_ampt_spatial: Spatially variable Green-Ampt data (F lines)
        - scs_global: Global SCS parameters (if applicable) 
        - scs_spatial: Spatially variable SCS curve numbers (S lines)
        - channel_reaches: Channel reach infiltration data (R lines)
        - channel_elements: Channel element infiltration data (C lines)
        - horton_global: Global Horton parameters (if applicable)
        - horton_spatial: Spatially variable Horton data (H lines)
        
    Raises:
        FileNotFoundError: If INFIL.DAT file is not found.
        ValueError: If file format is invalid.
    """
    infil_file = os.path.join(path, 'INFIL.DAT')
    
    if not os.path.exists(infil_file):
        raise FileNotFoundError(f"INFIL.DAT file not found at {infil_file}")
    
    logger.info(f"Extracting comprehensive infiltration data from {infil_file}")
    
    try:
        with open(infil_file, 'r') as file:
            lines = [line.strip() for line in file.readlines()]
    except IOError as e:
        raise IOError(f"Failed to read INFIL.DAT file: {e}")
    
    lines = [line for line in lines if line and not line.startswith('#')]
    
    if not lines:
        raise ValueError("INFIL.DAT file is empty or contains no valid data")
    
    try:
        infil_method = int(lines[0])
        if infil_method not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid infiltration method: {infil_method}")
    except (ValueError, IndexError) as e:
        raise ValueError(f"First line must contain valid infiltration method (1-4): {e}")
    
    logger.info(f"Processing infiltration method {infil_method}: {_get_infiltration_method_name(infil_method)}")
    
    result = {
        'method_info': {'infil_method': infil_method},
        'green_ampt_global': {},
        'green_ampt_spatial': pd.DataFrame(),
        'scs_global': {},
        'scs_spatial': pd.DataFrame(),
        'channel_reaches': pd.DataFrame(),
        'channel_elements': pd.DataFrame(),
        'horton_global': {},
        'horton_spatial': pd.DataFrame()
    }
    
    line_idx = 1
    
    if infil_method in [1, 3]:
        line_idx, ga_global = _parse_green_ampt_global(lines, line_idx)
        result['green_ampt_global'] = ga_global
    
    if infil_method in [2, 3]:
        line_idx, scs_global = _parse_scs_global(lines, line_idx)
        result['scs_global'] = scs_global
    
    if infil_method == 4:
        line_idx, horton_global = _parse_horton_global(lines, line_idx)
        result['horton_global'] = horton_global
    
    while line_idx < len(lines) and not lines[line_idx].startswith(('R', 'F', 'S', 'C', 'H')):
        line_idx += 1
    
    spatial_data = _parse_spatial_lines(lines[line_idx:])
    
    result['green_ampt_spatial'] = _create_green_ampt_df(spatial_data.get('F', []))
    result['scs_spatial'] = _create_scs_df(spatial_data.get('S', []))
    result['channel_reaches'] = _create_channel_reaches_df(spatial_data.get('R', []))
    result['channel_elements'] = _create_channel_elements_df(spatial_data.get('C', []))
    result['horton_spatial'] = _create_horton_df(spatial_data.get('H', []))
    
    logger.info(f"Extraction completed successfully. Green-Ampt: {len(result['green_ampt_spatial'])}, "
               f"SCS: {len(result['scs_spatial'])}, Reaches: {len(result['channel_reaches'])}, "
               f"Elements: {len(result['channel_elements'])}, Horton: {len(result['horton_spatial'])}")
    
    return result


def _parse_green_ampt_global(lines: List[str], start_idx: int) -> Tuple[int, Dict[str, float]]:
    """Parse Green-Ampt global parameters."""
    if start_idx >= len(lines):
        return start_idx, {}
    
    ga_params = lines[start_idx].split()
    global_params = {
        'abstr': float(ga_params[0]),
        'sati': float(ga_params[1]),
        'satf': float(ga_params[2]),
        'poros': float(ga_params[3]),
        'soild': float(ga_params[4]),
        'infchan': int(ga_params[5])
    }
    
    idx = start_idx + 1
    
    if idx < len(lines) and not lines[idx].startswith(('R', 'F', 'S', 'C', 'I', 'H')):
        hydc_params = lines[idx].split()
        global_params.update({
            'hydcall': float(hydc_params[0]),
            'soilall': float(hydc_params[1]),
            'hydcadj': float(hydc_params[2]) if len(hydc_params) > 2 else 0.0
        })
        idx += 1
    
    return idx, global_params


def _parse_scs_global(lines: List[str], start_idx: int) -> Tuple[int, Dict[str, float]]:
    """Parse SCS global parameters."""
    if start_idx >= len(lines):
        return start_idx, {}
    
    if lines[start_idx].startswith(('R', 'F', 'S', 'C', 'H')):
        return start_idx, {}
    
    scs_params = lines[start_idx].split()
    try:
        global_params = {
            'scsnall': float(scs_params[0]),
            'abstr1': float(scs_params[1])
        }
        return start_idx + 1, global_params
    except (ValueError, IndexError):
        return start_idx, {}


def _parse_horton_global(lines: List[str], start_idx: int) -> Tuple[int, Dict[str, float]]:
    """Parse Horton global parameters."""
    if start_idx >= len(lines):
        return start_idx, {}
    
    horton_params = lines[start_idx].split()
    global_params = {
        'fhortoni': float(horton_params[0]),
        'fhortonf': float(horton_params[1]),
        'decaya': float(horton_params[2])
    }
    
    return start_idx + 1, global_params


def _parse_spatial_lines(lines: List[str]) -> Dict[str, List[List[str]]]:
    """Parse all spatial/element-specific lines by type."""
    spatial_data = {'F': [], 'S': [], 'R': [], 'C': [], 'H': []}
    
    for line in lines:
        if not line:
            continue
            
        parts = line.split()
        if not parts:
            continue
            
        line_type = parts[0]
        if line_type in spatial_data:
            spatial_data[line_type].append(parts[1:])
    
    return spatial_data


def _get_infiltration_method_name(method_code: int) -> str:
    """Get human-readable infiltration method name."""
    methods = {
        1: "Green-Ampt",
        2: "SCS Curve Number", 
        3: "Combined Green-Ampt and SCS",
        4: "Horton"
    }
    return methods.get(method_code, f"Unknown ({method_code})")


def _create_green_ampt_df(f_lines: List[List[str]]) -> pd.DataFrame:
    """Create DataFrame for spatially variable Green-Ampt data (F lines)."""
    if not f_lines:
        return pd.DataFrame()
    
    columns = [GRID_ID, XKSAT, PSIF, DTHETA, ABSTRINF, RTIMPF, SOIL_DEPTH]
    df = pd.DataFrame(f_lines, columns=columns)
    
    numeric_columns = [XKSAT, PSIF, DTHETA, ABSTRINF, RTIMPF, SOIL_DEPTH]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df[GRID_ID] = pd.to_numeric(df[GRID_ID], errors='coerce').astype('Int64')
    
    return df


def _create_scs_df(s_lines: List[List[str]]) -> pd.DataFrame:
    """Create DataFrame for spatially variable SCS curve numbers (S lines)."""
    if not s_lines:
        return pd.DataFrame()
    
    columns = [GRID_ID, CURVE_NUMBER]
    df = pd.DataFrame(s_lines, columns=columns)
    
    df[GRID_ID] = pd.to_numeric(df[GRID_ID], errors='coerce').astype('Int64')
    df[CURVE_NUMBER] = pd.to_numeric(df[CURVE_NUMBER], errors='coerce')
    
    return df


def _create_channel_reaches_df(r_lines: List[List[str]]) -> pd.DataFrame:
    """Create DataFrame for channel reach infiltration data (R lines)."""
    if not r_lines:
        return pd.DataFrame()
    
    data = []
    for i, line_data in enumerate(r_lines):
        reach_data = {
            REACH_ID: i + 1,
            HYDCX_INITIAL: float(line_data[0]),
            HYDCX_FINAL: float(line_data[1]) if len(line_data) > 1 else None,
            SOIL_DEPTH: float(line_data[2]) if len(line_data) > 2 else None
        }
        data.append(reach_data)
    
    return pd.DataFrame(data)


def _create_channel_elements_df(c_lines: List[List[str]]) -> pd.DataFrame:
    """Create DataFrame for channel element infiltration data (C lines)."""
    if not c_lines:
        return pd.DataFrame()
    
    columns = [CHANNEL_ELEMENT, HYDCON]
    df = pd.DataFrame(c_lines, columns=columns)
    
    df[CHANNEL_ELEMENT] = pd.to_numeric(df[CHANNEL_ELEMENT], errors='coerce').astype('Int64')
    df[HYDCON] = pd.to_numeric(df[HYDCON], errors='coerce')
    
    return df


def _create_horton_df(h_lines: List[List[str]]) -> pd.DataFrame:
    """Create DataFrame for spatially variable Horton data (H lines)."""
    if not h_lines:
        return pd.DataFrame()
    
    columns = [GRID_ID, FHORTI, FHORTF, DECAY_COEFF]
    df = pd.DataFrame(h_lines, columns=columns)
    
    df[GRID_ID] = pd.to_numeric(df[GRID_ID], errors='coerce').astype('Int64')
    df[FHORTI] = pd.to_numeric(df[FHORTI], errors='coerce')
    df[FHORTF] = pd.to_numeric(df[FHORTF], errors='coerce')
    df[DECAY_COEFF] = pd.to_numeric(df[DECAY_COEFF], errors='coerce')
    
    return df


def summarize_infil_data(infil_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create summary statistics for infiltration data.
    
    Args:
        infil_data (Dict): Dictionary returned from extract_infil_dat_comprehensive.
        
    Returns:
        Dict: Summary statistics including method, counts, and parameter ranges.
    """
    method = infil_data['method_info']['infil_method']
    
    summary = {
        'infiltration_method': _get_infiltration_method_name(method),
        'method_code': method,
        'green_ampt_elements': len(infil_data['green_ampt_spatial']),
        'scs_elements': len(infil_data['scs_spatial']),
        'channel_reaches': len(infil_data['channel_reaches']),
        'channel_elements': len(infil_data['channel_elements']),
        'horton_elements': len(infil_data['horton_spatial'])
    }
    
    ga_df = infil_data['green_ampt_spatial']
    if not ga_df.empty:
        summary['hydraulic_conductivity_range'] = {
            'min': float(ga_df[XKSAT].min()),
            'max': float(ga_df[XKSAT].max()),
            'mean': float(ga_df[XKSAT].mean())
        }
        summary['soil_suction_range'] = {
            'min': float(ga_df[PSIF].min()),
            'max': float(ga_df[PSIF].max()),
            'mean': float(ga_df[PSIF].mean())
        }
    
    scs_df = infil_data['scs_spatial']
    if not scs_df.empty:
        summary['curve_number_range'] = {
            'min': float(scs_df[CURVE_NUMBER].min()),
            'max': float(scs_df[CURVE_NUMBER].max()),
            'mean': float(scs_df[CURVE_NUMBER].mean())
        }
    
    return summary


def validate_infil_data(infil_data: Dict[str, Any]) -> List[str]:
    """
    Validate infiltration data and return warnings.
    
    Args:
        infil_data (Dict): Dictionary returned from extract_infil_dat_comprehensive.
        
    Returns:
        List[str]: List of validation warning messages.
    """
    warnings = []
    method = infil_data['method_info']['infil_method']
    
    if method in [1, 3]:
        if not infil_data['green_ampt_global']:
            warnings.append("Green-Ampt method selected but no global parameters found")
        
        ga_df = infil_data['green_ampt_spatial']
        if not ga_df.empty:
            bad_k = ga_df[(ga_df[XKSAT] < 0.01) | (ga_df[XKSAT] > 10.0)]
            if not bad_k.empty:
                warnings.append(f"Unusual hydraulic conductivity values found for {len(bad_k)} elements")
            
            bad_psif = ga_df[(ga_df[PSIF] < 1.0) | (ga_df[PSIF] > 20.0)]
            if not bad_psif.empty:
                warnings.append(f"Unusual soil suction values found for {len(bad_psif)} elements")
    
    if method in [2, 3]:
        if not infil_data['scs_global']:
            warnings.append("SCS method selected but no global parameters found")
        
        scs_df = infil_data['scs_spatial']
        if not scs_df.empty:
            bad_cn = scs_df[(scs_df[CURVE_NUMBER] < 30) | (scs_df[CURVE_NUMBER] > 98)]
            if not bad_cn.empty:
                warnings.append(f"Unusual SCS curve numbers found for {len(bad_cn)} elements")
    
    return warnings

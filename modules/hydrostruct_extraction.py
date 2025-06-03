"""Module for reading and processing HYDROSTRUCT.OUT files from FLO-2D."""

import os
import pandas as pd
import re
from typing import Tuple, Dict, List

def hydrostruct_extract(file_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Read and process the HYDROSTRUCT.OUT file.
    
    Args:
        file_path (str): Path to the HYDROSTRUCT.OUT file
        
    Returns:
        tuple: (structure_info_df, time_series_df)
            - structure_info_df: DataFrame containing structure summary information
            - time_series_df: DataFrame containing time series data for all structures
    """
    structures = _process_file(file_path)
    return _create_structure_df(structures), _create_timeseries_df(structures)

def _process_file(file_path: str) -> List[Dict]:
    """
    Process the HYDROSTRUCT.OUT file content.
    
    Args:
        file_path (str): Path to the HYDROSTRUCT.OUT file
        
    Returns:
        List[Dict]: List of structure dictionaries containing header and time series data
    """
    structures = []
    current_structure = None
    
    with open(file_path, 'r') as file:
        lines = file.readlines()
        
    for line in lines:
        current_structure = _process_header(line, current_structure, structures)
        _process_timeseries(line, current_structure)
        
    # Add final structure if exists
    if current_structure:
        structures.append(current_structure)
        
    return structures

def _process_header(line: str, current_structure: Dict, structures: List[Dict]) -> Dict:
    """
    Process structure header information from a line.
    
    Args:
        line (str): Line from the file
        current_structure (Dict): Current structure being processed
        structures (List[Dict]): List of processed structures
        
    Returns:
        Dict: Updated current structure dictionary
    """
    max_discharge_match = re.search(
        r'THE MAXIMUM DISCHARGE FOR: (\S+)\s+STRUCTURE NO.\s+(\d+) IS:\s+([-\d.]+)\s+AT TIME:\s+([-\d.]+)',
        line
    )
    
    if max_discharge_match:
        if current_structure:
            structures.append(current_structure)
        
        structure_name, structure_no, max_discharge, peak_time = max_discharge_match.groups()
        return {
            'name': structure_name,
            'structure_no': int(structure_no),
            'max_discharge': float(max_discharge),
            'peak_time': float(peak_time),
            'time_series': []
        }
    
    return current_structure

def _process_timeseries(line: str, current_structure: Dict) -> None:
    """
    Process time series data from a line.
    
    Args:
        line (str): Line from the file
        current_structure (Dict): Current structure being processed
    """
    if not current_structure:
        return
        
    time_series_match = re.match(r'\s+(\d+\.\d+)\s+([-\d.]+)\s+([-\d.]+)', line)
    if time_series_match:
        time, inflow, outflow = time_series_match.groups()
        current_structure['time_series'].append({
            'time': float(time),
            'inflow': float(inflow),
            'outflow': float(outflow)
        })

def _create_structure_df(structures: List[Dict]) -> pd.DataFrame:
    """
    Create summary DataFrame for structure information.
    
    Args:
        structures (List[Dict]): List of structure dictionaries
        
    Returns:
        pd.DataFrame: Structure summary information
    """
    return pd.DataFrame([{
        'name': s['name'],
        'structure_no': s['structure_no'],
        'max_discharge': s['max_discharge'],
        'peak_time': s['peak_time']
    } for s in structures])

def _create_timeseries_df(structures: List[Dict]) -> pd.DataFrame:
    """
    Create time series DataFrame for all structures.
    
    Args:
        structures (List[Dict]): List of structure dictionaries
        
    Returns:
        pd.DataFrame: Time series data for all structures
    """
    time_series_data = []
    for structure in structures:
        for ts in structure['time_series']:
            time_series_data.append({
                'structure_name': structure['name'],
                'structure_no': structure['structure_no'],
                'time': ts['time'],
                'inflow': ts['inflow'],
                'outflow': ts['outflow']
            })
    
    return pd.DataFrame(time_series_data)

def main():
    """Example of reading and processing a HYDROSTRUCT.OUT file."""
    
    # Set up the file path
    base_path = r"R:\_anichols\Projects\AZ_7_RANCHES\FLO2D\20231212_Added_FPXSEC"
    hydrostruct_file = "HYDROSTRUCT.OUT"
    file_path = os.path.join(base_path, hydrostruct_file)
    
    # Read the HYDROSTRUCT.OUT file
    structure_info, time_series = read_hydrostruct(file_path)
    
    # Print structure summary information
    print("\nStructure Summary:")
    print(structure_info)
    
    # Print first few rows of time series data
    print("\nTime Series Data (first few rows):")
    print(time_series.head())

if __name__ == "__main__":
    main()
"""Reader for FLO-2D HYSTRUC.DAT files."""

import pandas as pd
from typing import Dict, List, Optional
import os

def hystruc_extract(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Read and parse HYSTRUC.DAT file.
    
    Args:
        file_path: Path to HYSTRUC.DAT file
        
    Returns:
        Dictionary containing DataFrames for:
        - structures: Main structure data
        - rating_curves: Rating curve data (type C)
        - replacement_curves: Replacement rating curve data (type R) 
        - rating_tables: Rating table data (type T)
        - culvert_data: Culvert equations data (type F)
        - storm_drain: Storm drain data (type D)
    """
    return _create_dataframes(_process_file(file_path))

def _process_file(file_path: str) -> Dict[str, List]:
    """Process HYSTRUC.DAT file content and collect data."""
    collectors = {
        'structures': [],
        'rating_curves': [],
        'replacement_curves': [],
        'rating_tables': [],
        'culvert_data': [],
        'storm_drain': []
    }
    
    current_structure = None
    
    with open(file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        parts = line.split()
        _process_line(parts, collectors, current_structure)
        if parts[0] == 'S':
            current_structure = collectors['structures'][-1]
            
    return collectors

@staticmethod
def _parse_structure(parts: List[str]) -> Dict:
    """
    Parse structure (S) line.
    
    Args:
        parts: Split line parts
        
    Returns:
        Dictionary containing structure data
        
    Format:
    S name type curve_type inflow_node outflow_node control_type head_ref length diameter
    """
    try:
        if len(parts) < 9:
            raise ValueError(f"Not enough parts in structure line. Expected 9, got {len(parts)}")
        
        return {
            'name': parts[1].strip(),
            'type': int(float(parts[2])),
            'curve_type': int(float(parts[3])),
            'inflow_node': int(float(parts[4])),
            'outflow_node': int(float(parts[5])),
            'control_type': int(float(parts[6])),
            'head_ref': float(parts[7]),
            'length': float(parts[8]),
            'diameter': float(parts[9]) if len(parts) > 9 else 0.0
        }
    except (IndexError, ValueError) as e:
        raise ValueError(f"Error parsing structure line: {parts}. Error: {str(e)}")

@staticmethod
def _parse_rating_curve(parts: List[str], structure: Dict) -> Dict:
    """Parse rating curve (C) line."""
    return {
        'structure_name': structure['name'],
        'hdepexc': float(parts[1]),
        'coefq': float(parts[2]),
        'expq': float(parts[3]),
        'coefa': float(parts[4]) if len(parts) > 4 else None,
        'expa': float(parts[5]) if len(parts) > 5 else None
    }

@staticmethod
def _parse_replacement_curve(parts: List[str], structure: Dict) -> Dict:
    """
    Parse replacement curve (R) line.
    
    Args:
        parts: Split line parts
        structure: Current structure data
        
    Returns:
        Dictionary containing replacement curve data
    """
    return {
        'structure_name': structure['name'],
        'hdepexc': float(parts[1]),
        'coefq': float(parts[2]),
        'expq': float(parts[3]),
        'coefa': float(parts[4]) if len(parts) > 4 else None,
        'expa': float(parts[5]) if len(parts) > 5 else None
    }

@staticmethod
def _parse_rating_table(parts: List[str], structure: Dict) -> Dict:
    """
    Parse rating table (T) line.
    
    Args:
        parts: Split line parts
        structure: Current structure data
        
    Returns:
        Dictionary containing rating table data
        
    Format:
    T depth discharge
    """
    return {
        'structure_name': structure['name'],
        'depth': float(parts[1]),
        'discharge': float(parts[2])
    }

@staticmethod
def _parse_culvert_data(parts: List[str], structure: Dict) -> Dict:
    """
    Parse culvert data (F) line.
    
    Args:
        parts: Split line parts
        structure: Current structure data
        
    Returns:
        Dictionary containing culvert equation data
        
    Format:
    F culvert_type entrance_coef manning_n num_barrels inlet_control_eq
    """
    return {
        'structure_name': structure['name'],
        'culvert_type': int(float(parts[1])),
        'entrance_coef': float(parts[2]),
        'manning_n': float(parts[3]),
        'num_barrels': float(parts[4]),
        'inlet_control_eq': int(float(parts[5])) if len(parts) > 5 else None
    }

@staticmethod
def _parse_storm_drain(parts: List[str], structure: Dict) -> Dict:
    """
    Parse storm drain (D) line.
    
    Args:
        parts: Split line parts
        structure: Current structure data
        
    Returns:
        Dictionary containing storm drain data
    """
    return {
        'structure_name': structure['name'],
        'drain_type': int(parts[1]),
        'inlet_coef': float(parts[2]),
        'num_inlets': int(parts[3]),
        'inlet_area': float(parts[4]),
        'weir_length': float(parts[5]) if len(parts) > 5 else None,
        'orifice_area': float(parts[6]) if len(parts) > 6 else None
    }

def _process_line(parts: List[str], collectors: Dict[str, List], current_structure: Optional[Dict]) -> None:
    """Process a single line from the HYSTRUC.DAT file."""
    try:
        identifier = parts[0]
        
        if identifier == 'S':
            collectors['structures'].append(_parse_structure(parts))
        elif identifier == 'C' and current_structure:
            collectors['rating_curves'].append(_parse_rating_curve(parts, current_structure))
        elif identifier == 'R' and current_structure:
            collectors['replacement_curves'].append(_parse_replacement_curve(parts, current_structure))
        elif identifier == 'T' and current_structure:
            collectors['rating_tables'].append(_parse_rating_table(parts, current_structure))
        elif identifier == 'F' and current_structure:
            collectors['culvert_data'].append(_parse_culvert_data(parts, current_structure))
        elif identifier == 'D' and current_structure:
            collectors['storm_drain'].append(_parse_storm_drain(parts, current_structure))
    except Exception as e:
        raise

def _create_dataframes(collectors: Dict[str, List]) -> Dict[str, pd.DataFrame]:
    """Convert collected data to DataFrames."""
    dfs = {
        name: pd.DataFrame(data)
        for name, data in collectors.items()
    }
    return {k:v for k,v in dfs.items() if not v.empty}

if __name__ == "__main__":
    folder_path = r"R:\_anichols\Projects\AZ_7_RANCHES\FLO2D\20231212_Added_FPXSEC"
    hystruc_file = "HYSTRUC.DAT"
    file_path = os.path.join(folder_path, hystruc_file)

    # Read the HYSTRUC.DAT file
    hystruc_data = hystruc_extract(file_path)

    # Access different structure types
    structures_df = hystruc_data['structures']
    rating_tables_df = hystruc_data['rating_tables']
    culvert_data_df = hystruc_data['culvert_data']

    # Example: Print basic information about structures
    print("\nStructures Summary:")
    print(f"Number of structures: {len(structures_df)}")
    print("\nFirst few structures:")
    print(structures_df.head())

    # Example: Look at rating curves for a specific structure
    structure_name = structures_df['name'].iloc[0]  # Get first structure name
    print(f"\nRating tables for structure {structure_name}:")
    structure_tables = rating_tables_df[rating_tables_df['structure_name'] == structure_name]
    print(structure_tables)

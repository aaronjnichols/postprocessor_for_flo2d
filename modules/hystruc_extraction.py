import os
import pandas as pd
import re
import logging
from modules.utilities import time_function
from .constants import (
    STRUCTURE_ID,
    INFLOW_NODE,
    OUTFLOW_NODE,
    STRUCTURE_TYPE,
    STAGE,
    FLOW,
    IFPROCHAN,
    ICURVETABLE,
    INOUTCONT,
    HEADREFEL,
    CLENGTH,
    CDIAMETER,
    TYPEC,
    TYPEEN,
    CULVERTN,
    KE,
    CUBASE,
    ISTORMDOUT,
    STORMDMAXQ,
    HDEPEXC,
    COEFQ,
    EXPQ,
    COEFA,
    EXPA,
    REPDEP,
    RQCOEFQ,
    RQEXP,
    RACOEF,
    RAEXP,
    ATABLE,
    normalize_grid_id,
)

# Set up logger
logger = logging.getLogger('FLO2D_Postprocessor')

def create_structure_template():
    """Create a template dictionary with all possible structure fields."""
    return {
        STRUCTURE_ID: None,
        IFPROCHAN: None,
        ICURVETABLE: None,
        INFLOW_NODE: None,
        OUTFLOW_NODE: None,
        INOUTCONT: None,
        HEADREFEL: None,
        CLENGTH: None,
        CDIAMETER: None,
        TYPEC: None,
        TYPEEN: None,
        CULVERTN: None,
        KE: None,
        CUBASE: None,
        ISTORMDOUT: None,
        STORMDMAXQ: None
    }

def parse_structure_line(line_parts):
    """Parse S line - Structure definition."""
    try:
        if len(line_parts) < 10:
            raise ValueError(f"S line requires 10 fields, got {len(line_parts)}")
        
        structure = create_structure_template()
        structure.update({
            STRUCTURE_ID: line_parts[1],
            IFPROCHAN: int(line_parts[2]),
            ICURVETABLE: int(line_parts[3]),
            INFLOW_NODE: normalize_grid_id(int(line_parts[4])),
            OUTFLOW_NODE: normalize_grid_id(int(line_parts[5])),
            INOUTCONT: int(line_parts[6]),
            HEADREFEL: float(line_parts[7]),
            CLENGTH: float(line_parts[8]),
            CDIAMETER: float(line_parts[9])
        })
        return structure
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing S line: {' '.join(line_parts)}. Error: {e}")
        return None

def parse_rating_curve_line(line_parts, structure_name):
    """Parse C line - Rating curve data."""
    try:
        if len(line_parts) < 4:
            # Handle case where COEFA and EXPA might be missing (when CLENGTH = 0)
            if len(line_parts) >= 3:
                return {
                    'structure_name': structure_name,
                    HDEPEXC: float(line_parts[1]),
                    COEFQ: float(line_parts[2]),
                    EXPQ: float(line_parts[3]),
                    COEFA: None,
                    EXPA: None
                }
            else:
                raise ValueError(f"C line requires at least 3 fields, got {len(line_parts)}")
        else:
            return {
                'structure_name': structure_name,
                HDEPEXC: float(line_parts[1]),
                COEFQ: float(line_parts[2]),
                EXPQ: float(line_parts[3]),
                COEFA: float(line_parts[4]) if len(line_parts) > 4 else None,
                EXPA: float(line_parts[5]) if len(line_parts) > 5 else None
            }
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing C line: {' '.join(line_parts)}. Error: {e}")
        return None

def parse_replacement_curve_line(line_parts, structure_name):
    """Parse R line - Replacement rating curve data."""
    try:
        if len(line_parts) < 4:
            # Handle case where RACOEF and RAEXP might be missing (when CLENGTH = 0)
            if len(line_parts) >= 3:
                return {
                    'structure_name': structure_name,
                    REPDEP: float(line_parts[1]),
                    RQCOEFQ: float(line_parts[2]),
                    RQEXP: float(line_parts[3]),
                    RACOEF: None,
                    RAEXP: None
                }
            else:
                raise ValueError(f"R line requires at least 3 fields, got {len(line_parts)}")
        else:
            return {
                'structure_name': structure_name,
                REPDEP: float(line_parts[1]),
                RQCOEFQ: float(line_parts[2]),
                RQEXP: float(line_parts[3]),
                RACOEF: float(line_parts[4]) if len(line_parts) > 4 else None,
                RAEXP: float(line_parts[5]) if len(line_parts) > 5 else None
            }
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing R line: {' '.join(line_parts)}. Error: {e}")
        return None

def parse_rating_table_line(line_parts, structure_name):
    """Parse T line - Rating table data."""
    try:
        if len(line_parts) < 3:
            raise ValueError(f"T line requires at least 2 fields, got {len(line_parts)}")
        
        return {
            'structure_name': structure_name,
            STAGE: float(line_parts[1]),
            FLOW: float(line_parts[2]),
            ATABLE: float(line_parts[3]) if len(line_parts) > 3 else None
        }
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing T line: {' '.join(line_parts)}. Error: {e}")
        return None

def parse_culvert_line(line_parts, structure_name):
    """Parse F line - Culvert equations data."""
    try:
        if len(line_parts) < 6:
            raise ValueError(f"F line requires 6 fields, got {len(line_parts)}")
        
        return {
            'structure_name': structure_name,
            TYPEC: int(line_parts[1]),
            TYPEEN: int(line_parts[2]),
            CULVERTN: float(line_parts[3]),
            KE: float(line_parts[4]),
            CUBASE: float(line_parts[5])
        }
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing F line: {' '.join(line_parts)}. Error: {e}")
        return None

def parse_storm_drain_line(line_parts, structure_name):
    """Parse D line - Storm drain data."""
    try:
        if len(line_parts) < 3:
            raise ValueError(f"D line requires 3 fields, got {len(line_parts)}")
        
        return {
            'structure_name': structure_name,
            ISTORMDOUT: int(line_parts[1]),
            STORMDMAXQ: float(line_parts[2])
        }
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing D line: {' '.join(line_parts)}. Error: {e}")
        return None

@time_function
def extract_hystruc_results(file_path):
    """
    Extract hydraulic structure data from HYSTRUC.DAT file.
    
    Args:
        file_path (str): Path to directory containing HYSTRUC.DAT
        
    Returns:
        tuple: (structures_df, rating_curves) where:
            - structures_df: DataFrame with structure definitions
            - rating_curves: List of dicts with structure rating curve data for backward compatibility
    """
    hystruc_file_path = os.path.join(file_path, 'HYSTRUC.DAT')
    
    if not os.path.exists(hystruc_file_path):
        logger.error(f"HYSTRUC.DAT not found at {hystruc_file_path}")
        return pd.DataFrame(), []
    
    # Data containers
    structures = {}
    rating_curves_data = {}
    replacement_curves_data = {}
    rating_tables_data = {}
    culvert_data = {}
    storm_drain_data = {}
    
    current_structure = None
    
    try:
        with open(hystruc_file_path, 'r') as file:
            lines = file.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            line_parts = line.split()
            if not line_parts:
                continue
                
            line_type = line_parts[0].upper()
            
            try:
                if line_type == 'S':
                    # Structure definition
                    structure = parse_structure_line(line_parts)
                    if structure:
                        structure_name = structure[STRUCTURE_ID]
                        structures[structure_name] = structure
                        current_structure = structure_name
                        logger.debug(f"Parsed structure: {structure_name}")
                
                elif line_type == 'C':
                    # Rating curve
                    if current_structure:
                        curve_data = parse_rating_curve_line(line_parts, current_structure)
                        if curve_data:
                            if current_structure not in rating_curves_data:
                                rating_curves_data[current_structure] = []
                            rating_curves_data[current_structure].append(curve_data)
                
                elif line_type == 'R':
                    # Replacement rating curve
                    if current_structure:
                        replacement_data = parse_replacement_curve_line(line_parts, current_structure)
                        if replacement_data:
                            if current_structure not in replacement_curves_data:
                                replacement_curves_data[current_structure] = []
                            replacement_curves_data[current_structure].append(replacement_data)
                
                elif line_type == 'T':
                    # Rating table
                    if current_structure:
                        table_data = parse_rating_table_line(line_parts, current_structure)
                        if table_data:
                            if current_structure not in rating_tables_data:
                                rating_tables_data[current_structure] = []
                            rating_tables_data[current_structure].append(table_data)
                
                elif line_type == 'F':
                    # Culvert equations
                    if current_structure:
                        culvert_info = parse_culvert_line(line_parts, current_structure)
                        if culvert_info:
                            culvert_data[current_structure] = culvert_info
                            # Update structure with culvert data for backward compatibility
                            if current_structure in structures:
                                structures[current_structure].update({
                                    TYPEC: culvert_info[TYPEC],
                                    TYPEEN: culvert_info[TYPEEN],
                                    CULVERTN: culvert_info[CULVERTN],
                                    KE: culvert_info[KE],
                                    CUBASE: culvert_info[CUBASE]
                                })
                
                elif line_type == 'D':
                    # Storm drain
                    if current_structure:
                        storm_data = parse_storm_drain_line(line_parts, current_structure)
                        if storm_data:
                            storm_drain_data[current_structure] = storm_data
                            # Update structure with storm drain data
                            if current_structure in structures:
                                structures[current_structure].update({
                                    ISTORMDOUT: storm_data[ISTORMDOUT],
                                    STORMDMAXQ: storm_data[STORMDMAXQ]
                                })
                
                else:
                    logger.debug(f"Unknown line type '{line_type}' at line {line_num}: {line}")
                    
            except Exception as e:
                logger.warning(f"Error processing line {line_num}: {line}. Error: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error reading HYSTRUC.DAT file: {e}")
        return pd.DataFrame(), []
    
    # Create structures DataFrame
    if structures:
        structures_df = pd.DataFrame(list(structures.values()))
    else:
        structures_df = pd.DataFrame()
        logger.warning("No valid structures found in HYSTRUC.DAT")
    
    # Create backward-compatible rating curves format
    rating_curves = []
    
    # Process rating tables (T lines) for backward compatibility
    for structure_name, table_data in rating_tables_data.items():
        if table_data:
            df_data = []
            for entry in table_data:
                df_data.append([entry[STAGE], entry[FLOW]])
            
            if df_data:
                rating_curves.append({
                    STRUCTURE_ID: structure_name,
                    "Data": pd.DataFrame(df_data, columns=[STAGE, FLOW])
                })
    
    logger.info(f"Extracted {len(structures)} structures, {len(rating_curves)} rating curves, "
               f"{len(rating_curves_data)} rating curve definitions, {len(replacement_curves_data)} replacement curves, "
               f"{len(culvert_data)} culvert definitions, {len(storm_drain_data)} storm drain definitions")
    
    return structures_df, rating_curves

@time_function  
def extract_rating_curves(file_path):
    """
    Extract rating curves from the HYSTRUC.DAT file. 
    This function is maintained for backward compatibility.
    
    Args:
        file_path (str): Path to the HYSTRUC.DAT file.

    Returns:
        list: A list of dictionaries where each entry contains the structure name and its associated rating curve data.
    """
    # Use the enhanced extraction and return just the rating curves part
    _, rating_curves = extract_hystruc_results(os.path.dirname(file_path))
    return rating_curves

def get_comprehensive_structure_data(file_path):
    """
    Get comprehensive structure data including all extracted information.
    This is a new function that provides access to all extracted data types.
    
    Args:
        file_path (str): Path to directory containing HYSTRUC.DAT
        
    Returns:
        dict: Comprehensive data structure with all extracted information
    """
    hystruc_file_path = os.path.join(file_path, 'HYSTRUC.DAT')
    
    if not os.path.exists(hystruc_file_path):
        return {
            'structures_df': pd.DataFrame(),
            'rating_curves': [],
            'rating_curves_data': {},
            'replacement_curves_data': {},
            'rating_tables_data': {},
            'culvert_data': {},
            'storm_drain_data': {}
        }
    
    # For now, return the basic extraction - this could be enhanced later if needed
    structures_df, rating_curves = extract_hystruc_results(file_path)
    
    return {
        'structures_df': structures_df,
        'rating_curves': rating_curves,
        'rating_curves_data': {},
        'replacement_curves_data': {},
        'rating_tables_data': {},
        'culvert_data': {},
        'storm_drain_data': {}
    }

# If you want to test the functions when the script is run directly
if __name__ == "__main__":
    test_file_path = "path/to/your/HYSTRUC.DAT"  # Replace with an actual test file path
    df, rating_curves = extract_hystruc_results(os.path.dirname(test_file_path))
    print(f"Extracted {len(df)} structures")
    print(f"Extracted {len(rating_curves)} rating curves")
    if not df.empty:
        print("\nStructure columns:", list(df.columns))
        print("\nFirst few structures:")
        print(df.head())
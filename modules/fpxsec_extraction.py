import pandas as pd
from typing import Dict, List
import logging

def fpxsec_extract(fpxsec_file: str) -> pd.DataFrame:
    """
    Extract cross section data from FPXSEC.DAT file.
    
    Args:
        fpxsec_file (str): Path to FPXSEC.DAT file
        
    Returns:
        pd.DataFrame: DataFrame containing cross section data with start_cell and end_cell
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    try:
        # Read FPXSEC.DAT
        with open(fpxsec_file, 'r') as f:
            lines = f.readlines()
            
        logger.debug(f"Read {len(lines)} lines from {fpxsec_file}")
        
        data = []
        for i, line in enumerate(lines):
            if i < 5:
                logger.debug(f"Line {i+1}: {line.strip()}")
                
            if line.strip() and line.startswith('X'):
                values = line.strip().split()
                
                try:
                    flow_direction = int(values[1])
                    num_points = int(values[2])
                    grid_ids = [int(val) for val in values[3:3+num_points]]
                    
                    # Extract start and end cells based on flow direction
                    if flow_direction in [1, 3]:  # Non-adjacent cells
                        start_cell = grid_ids[0]
                        end_cell = grid_ids[-1]
                    else:  # Adjacent cells (flow_direction = 4)
                        start_cell = min(grid_ids)
                        end_cell = max(grid_ids)
                    
                    data.append({
                        'flow_direction': flow_direction,
                        'num_points': num_points,
                        'grid_ids': grid_ids,
                        'start_cell': start_cell,
                        'end_cell': end_cell
                    })
                    
                    logger.debug(f"Processed line {i+1}: flow_direction={flow_direction}, "
                               f"start_cell={start_cell}, end_cell={end_cell}")
                               
                except Exception as e:
                    logger.error(f"Error parsing line {i+1}: {line.strip()} - {str(e)}")
                    continue
                    
        df = pd.DataFrame(data)
        
        if len(df) > 0:
            df['fpxs_id'] = range(1, len(df) + 1)
            logger.info(f"Successfully extracted {len(df)} cross sections from FPXSEC.DAT")
        else:
            logger.warning("No valid cross sections found in FPXSEC.DAT")
            
        # Debug print the first few rows
        if not df.empty:
            logger.debug("First few rows of extracted data:")
            logger.debug(df[['fpxs_id', 'flow_direction', 'start_cell', 'end_cell']].head())
            
        return df
        
    except Exception as e:
        logger.error(f"Error extracting FPXSEC.DAT: {str(e)}")
        return pd.DataFrame(columns=['flow_direction', 'num_points', 'grid_ids', 
                                   'start_cell', 'end_cell', 'fpxs_id'])

def _process_file(file_path: str) -> Dict:
    """
    Process FPXSEC.DAT file content.
    
    Args:
        file_path (str): Path to FPXSEC.DAT file
        
    Returns:
        Dict: Dictionary containing processed section data
    """
    sections = {}
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        if line.startswith('X'):
            section = _process_section_line(line, len(sections) + 1)
            sections[section['fpxs_id']] = section
            
    return sections

def _process_section_line(line: str, section_id: int) -> Dict:
    """
    Process a cross section line from the file.
    
    Args:
        line (str): Line from FPXSEC.DAT file
        section_id (int): ID for the current section
        
    Returns:
        Dict: Dictionary containing processed line data
    """
    parts = line.strip().split()
    flow_direction = int(parts[1])
    num_points = int(parts[2])
    
    # Convert grid IDs to integers
    grid_ids = [int(float(x)) for x in parts[3:3+num_points]]
    
    return {
        'fpxs_id': section_id,
        'flow_direction': flow_direction,
        'grid_ids': grid_ids
    }

def _create_sections_df(sections: Dict) -> pd.DataFrame:
    """
    Create DataFrame from sections data.
    
    Args:
        sections (Dict): Dictionary containing section data
        
    Returns:
        pd.DataFrame: DataFrame containing section data
    """
    if not sections:
        return pd.DataFrame()
        
    return pd.DataFrame.from_dict(sections, orient='index')

# Example usage
if __name__ == "__main__":
    # Example file path
    fpxsec_path = r"R:\_anichols\Projects\_flo2d_postprocessor_tests\Detroit_Basin_Prop100y24h/FPXSEC.DAT"
    
    try:
        # Read the FPXSEC.DAT file into a DataFrame
        fpxsec_df = fpxsec_extract(fpxsec_path)
        
        # Display basic information about the DataFrame
        print("DataFrame Info:") # debug print
        print(fpxsec_df.info()) # debug print
        
        # Display first few rows of the DataFrame
        print("\nFirst few rows of the DataFrame:") # debug print
        print(fpxsec_df[['fpxs_id', 'flow_direction', 'start_cell', 'end_cell']].head()) # debug print
        
    except FileNotFoundError:
        print(f"Error: Could not find FPXSEC.DAT file at {fpxsec_path}")
    except Exception as e:
        print(f"Error processing file: {str(e)}")
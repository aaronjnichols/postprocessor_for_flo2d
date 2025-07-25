import os
import pandas as pd
import re
from modules.utilities import time_function
from .constants import (
    STRUCTURE_ID,
    INFLOW_NODE,
    OUTFLOW_NODE,
    STRUCTURE_TYPE,
    STAGE,
    FLOW,
    normalize_grid_id,
)

@time_function
def extract_hystruc_results(file_path):
    hystruc_file_path = os.path.join(file_path, 'HYSTRUC.DAT')

    # Extract data from HYSTRUC.DAT file
    with open(hystruc_file_path, 'r') as file:
        lines = file.readlines()

    structures = {}

    for line in lines:
        line = line.strip().split()

        if line[0] == 'S':
            structure_name = line[1]
            if structure_name not in structures:
                            structures[structure_name] = {
                'structure_name': structure_name,
                'ifprochan': int(line[2]),
                'icurvetable': int(line[3]),
                INFLOW_NODE: normalize_grid_id(int(line[4])),
                OUTFLOW_NODE: normalize_grid_id(int(line[5])),
                'inoutcont': int(line[6]),
                'headrefel': float(line[7]),
                'clength': float(line[8]),
                'cdiameter': float(line[9]),
                'typec': None,
                'typeen': None,
                'culvertn': None,
                'ke': None,
                'cubase': None
            }

        elif line[0] == 'F' and structure_name in structures:
            structures[structure_name].update({
                'typec': int(line[1]),
                'typeen': int(line[2]),
                'culvertn': float(line[3]),
                'ke': float(line[4]),
                'cubase': float(line[5])
            })

    # Extract rating curves
    rating_curves = extract_rating_curves(hystruc_file_path)

    # Combine all extracted data
    df = pd.DataFrame(list(structures.values()))

    return df, rating_curves

@time_function
def extract_rating_curves(file_path):
    """
    Extract rating curves from the HYSTRUC.DAT file. Each curve contains stage-flow data.
    
    Args:
    file_path (str): Path to the HYSTRUC.DAT file.

    Returns:
    list: A list of dictionaries where each entry contains the structure name and its associated rating curve data.
    """
    rating_curves = []
    current_structure = None
    structure_data = []

    # Define regex patterns for identifying lines
    structure_pattern = re.compile(r"^S\s+(\w+)")
    data_pattern = re.compile(r"^T\s+([\d.]+)\s+([\d.]+)")
    
    with open(file_path, 'r') as file:
        for line in file:
            structure_match = structure_pattern.match(line)
            data_match = data_pattern.match(line)
            
            if structure_match:
                # If there was a previous structure with rating data, save it
                if current_structure and structure_data:
                    rating_curves.append({
                        STRUCTURE_ID: current_structure,
                        "Data": pd.DataFrame(structure_data, columns=[STAGE, FLOW])
                    })
                
                # Start new structure
                current_structure = structure_match.group(1)
                structure_data = []  # Reset data for new structure
            
            elif data_match:
                # Collect stage and flow data for the current structure
                stage = float(data_match.group(1))
                flow = float(data_match.group(2))
                structure_data.append([stage, flow])
        
        # Append the last structure's data if it exists
        if current_structure and structure_data:
            rating_curves.append({
                STRUCTURE_ID: current_structure,
                "Data": pd.DataFrame(structure_data, columns=[STAGE, FLOW])
            })
    
    return rating_curves

# If you want to test the functions when the script is run directly
if __name__ == "__main__":
    test_file_path = "path/to/your/HYSTRUC.DAT"  # Replace with an actual test file path
    df, rating_curves = extract_hystruc_results(os.path.dirname(test_file_path))
    print(df.head())
    print(f"\nNumber of rating curves extracted: {len(rating_curves)}")
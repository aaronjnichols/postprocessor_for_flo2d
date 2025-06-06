import os
import pandas as pd


def extract_super_out(path):
    super_file = os.path.join(path, 'SUPER.OUT')
    with open(super_file, 'r') as file:
        lines = file.readlines()

    data = []
    
    # Look for data sections dynamically
    in_data_section = False
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Check if we're entering a data section (look for the column header line)
        if "NODE    MAX FROUDE NO     DEPTH" in line:
            in_data_section = True
            continue
            
        # Check if we're starting a new section (reset flag for channel section)
        if line.startswith("TOP ") and "SUPERCRITICAL" in line:
            in_data_section = False
            continue
        
        # If we're in a data section, try to parse the line
        if in_data_section:
            parts = line.split()
            if len(parts) == 5:
                try:
                    # Try to parse as numeric data
                    grid_id = int(parts[0]) - 1  # Convert to 0-based indexing
                    max_froude_no = float(parts[1])
                    depth_super = float(parts[2])
                    time_super = float(parts[3])
                    num_supercritical_timesteps = int(parts[4])
                    
                    data.append({
                        'grid_id': grid_id,
                        'max_froude_no': max_froude_no,
                        'depth_super': depth_super,
                        'time_super': time_super,
                        'num_supercritical_timesteps': num_supercritical_timesteps
                    })
                except ValueError:
                    # Skip lines with non-numeric data (headers, etc.)
                    continue
    
    return pd.DataFrame(data)

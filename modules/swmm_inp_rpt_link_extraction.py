import re
import pandas as pd
import os

def _extract_link_summary(folder_path: str) -> pd.DataFrame:
    """
    Extract conduit data from SWMM.inp file.
    
    Args:
        folder_path (str): Path to folder containing SWMM.inp file
        
    Returns:
        pd.DataFrame: DataFrame containing conduit information with columns:
            Link_Name, From_Node, To_Node, Link_Type, Length, Roughness
    """
    # Read the INP file
    inp_file_path = os.path.join(folder_path, "SWMM.inp")
    with open(inp_file_path, 'r') as f:
        inp_content = f.readlines()

    # Extract the [CONDUITS] section
    start_marker = "[CONDUITS]"
    end_marker = "["
    conduits_data = []
    recording = False
    
    for line in inp_content:
        line = line.strip()
        if line.startswith(start_marker):
            recording = True
            continue
        elif recording and line.startswith(end_marker):
            break
        elif recording and not line.startswith(";;") and line:  # Skip comments and empty lines
            conduits_data.append(line)

    # Parse the conduits data
    link_summary_data = []
    for line in conduits_data:
        parts = re.split(r'\s+', line)
        if len(parts) >= 5:  # Minimum required fields
            try:
                link_name = parts[0]
                from_node = parts[1]
                to_node = parts[2]
                length = float(parts[3])
                roughness = float(parts[4])  # Manning's n
                inlet_offset = float(parts[5])
                outlet_offset = float(parts[6])
                init_flow = float(parts[7])
                max_flow = float(parts[8])
                
                link_summary_data.append([
                    link_name, 
                    from_node, 
                    to_node, 
                    'CONDUIT',  # All entries in [CONDUITS] section are conduits
                    length,
                    roughness,
                    inlet_offset,
                    outlet_offset,
                    init_flow,
                    max_flow
                ])
            except (ValueError, IndexError):
                print(f"Warning: Could not parse line: {line}")  # debug print
                continue

    # Create DataFrame with consistent column names
    columns = ["link_id", "from_node", "to_node", "type", "length", "n_value", "in_offset", "out_offset", "init_flow", "max_flow"]
    return pd.DataFrame(link_summary_data, columns=columns)

# Link Flow Summary Extraction

def _extract_link_flow_summary(content, start_index):
    separator_marker = "-----------------------------------------------------------------------------"
    link_flow_data = []
    recording = False
    pattern = re.compile(
        r"(\S+)\s+(\S+)\s+([\d.]+)\s+(\d+)\s+([\d:]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"
    )

    for line in content[start_index:]:
        if separator_marker in line:
            recording = True
            continue
        elif recording and line.strip() == "":
            break
        elif recording:
            match = pattern.search(line)
            if match:
                try:
                    link_name = match.group(1)
                    link_type = match.group(2)
                    max_flow = float(match.group(3))
                    day_max_flow = int(match.group(4))
                    time_of_max_flow = match.group(5)
                    max_velocity = float(match.group(6))
                    max_flow_ratio = float(match.group(7))
                    max_depth_ratio = float(match.group(8))
                    link_flow_data.append([link_name, link_type, max_flow, day_max_flow, time_of_max_flow, max_velocity, max_flow_ratio, max_depth_ratio])
                except ValueError:
                    continue

    columns = ["link_id", "type", "max_flow", "day_max", "time_max", "max_vel", 
              "flow_ratio", "depth_rat"]
    return pd.DataFrame(link_flow_data, columns=columns)

# Conduit Surcharge Summary Extraction

def _extract_conduit_surcharge_summary(content, start_index):
    separator_marker = "----------------------------------------------------------------------------"
    conduit_surcharge_data = []
    recording = False
    pattern = re.compile(
        r"(\S+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"
    )

    for line in content[start_index:]:
        if separator_marker in line:
            recording = True
            continue
        elif recording and line.strip() == "":
            break
        elif recording:
            match = pattern.search(line)
            if match:
                try:
                    conduit_name = match.group(1)
                    hours_full_both_ends = float(match.group(2))
                    hours_full_upstream = float(match.group(3))
                    hours_full_downstream = float(match.group(4))
                    hours_above_full_normal_flow = float(match.group(5))
                    hours_capacity_limited = float(match.group(6))
                    conduit_surcharge_data.append([conduit_name, hours_full_both_ends, hours_full_upstream, hours_full_downstream, hours_above_full_normal_flow, hours_capacity_limited])
                except ValueError:
                    continue

    columns = ["link_id", "hrs_full", "hrs_full_u", "hrs_full_d", "hrs_above", "hrs_cap"]
    return pd.DataFrame(conduit_surcharge_data, columns=columns)

# Flow Classification Summary Extraction

def _extract_flow_classification_summary(content, start_index):
    separator_marker = "-----------------------------------------------------------------------------------------"
    flow_classification_data = []
    recording = False
    pattern = re.compile(
        r"(\S+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"
    )

    for line in content[start_index:]:
        if separator_marker in line:
            recording = True
            continue
        elif recording and line.strip() == "":
            break
        elif recording:
            match = pattern.search(line)
            if match:
                try:
                    conduit_name = match.group(1)
                    adjusted_actual_length = float(match.group(2))
                    fraction_dry_up = float(match.group(3))
                    fraction_dry_down = float(match.group(4))
                    fraction_dry_sub = float(match.group(5))
                    fraction_dry_sup = float(match.group(6))
                    fraction_crit_up = float(match.group(7))
                    fraction_crit_down = float(match.group(8))
                    avg_froude_number = float(match.group(9))
                    avg_flow_change = float(match.group(10))
                    flow_classification_data.append([conduit_name, adjusted_actual_length, fraction_dry_up, fraction_dry_down, fraction_dry_sub, fraction_dry_sup, fraction_crit_up, fraction_crit_down, avg_froude_number, avg_flow_change])
                except ValueError:
                    continue

    columns = ["link_id", "adj_len", "dry_up", "dry_down", "dry_sub", "dry_sup", 
              "crit_up", "crit_down", "froude", "flow_chg"]
    return pd.DataFrame(flow_classification_data, columns=columns)

# Find Section Start Index

def _find_section_start(content, section_title):
    for index, line in enumerate(content):
        if section_title in line:
            return index
    return None

# Main Extraction Function

def extract_link_data(folder_path):
    """
    Extract all SWMM summaries and merge them into a single DataFrame.
    
    Args:
        folder_path (str): Path to folder containing SWMM files
        
    Returns:
        pd.DataFrame: Merged DataFrame containing all SWMM data
    """
    # Extract link data from INP file
    link_summary_df = _extract_link_summary(folder_path)
    
    # Extract other summaries from RPT file
    rpt_file_path = os.path.join(folder_path, "swmm.RPT")
    with open(rpt_file_path, 'r') as f:
        rpt_content = f.readlines()
    
    link_flow_start_index = _find_section_start(rpt_content, "Link Flow Summary")
    link_flow_summary_df = _extract_link_flow_summary(rpt_content, link_flow_start_index) if link_flow_start_index else pd.DataFrame()
    
    conduit_surcharge_start_index = _find_section_start(rpt_content, "Conduit Surcharge Summary")
    conduit_surcharge_summary_df = _extract_conduit_surcharge_summary(rpt_content, conduit_surcharge_start_index) if conduit_surcharge_start_index else pd.DataFrame()
    
    flow_classification_start_index = _find_section_start(rpt_content, "Flow Classification Summary")
    flow_classification_summary_df = _extract_flow_classification_summary(rpt_content, flow_classification_start_index) if flow_classification_start_index else pd.DataFrame()

    # Merge all dataframes based on link name
    merged_df = link_summary_df
    
    if not link_flow_summary_df.empty:
        merged_df = merged_df.merge(link_flow_summary_df, 
                                  left_on='link_id', 
                                  right_on='link_id', 
                                  how='left')
                                  
    if not conduit_surcharge_summary_df.empty:
        merged_df = merged_df.merge(conduit_surcharge_summary_df,
                                  left_on='link_id',
                                  right_on='link_id',
                                  how='left')
                                  
    if not flow_classification_summary_df.empty:
        merged_df = merged_df.merge(flow_classification_summary_df,
                                  left_on='link_id', 
                                  right_on='link_id',
                                  how='left')

    return merged_df


if __name__ == "__main__":
    # Example usage
    folder_path = r"R:\_anichols\Projects\_flo2d_postprocessor_tests\Detroit_Basin_Prop100y24h"

    # Extract all summaries
    summary_data = extract_link_data(folder_path)
    print(summary_data)



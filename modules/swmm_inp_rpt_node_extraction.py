import re
import pandas as pd
import os

def _extract_node_summary(content):
    start_marker = "Node Summary"
    dashes_marker = "------------------"
    blank_line_marker = ""
    node_summary_data = []
    recording = False
    for line in content:
        if start_marker in line:
            recording = True
            continue
        elif recording and dashes_marker in line:
            continue
        elif recording and line.strip() == blank_line_marker:
            break
        elif recording:
            parts = line.split()
            if len(parts) >= 5:
                try:
                    name = parts[0]
                    type_ = parts[1]
                    invert_elev = float(parts[2])
                    max_depth = float(parts[3])
                    ponded_area = float(parts[4])
                    external_inflow = None
                    node_summary_data.append([name, type_, invert_elev, max_depth, ponded_area, external_inflow])
                except ValueError:
                    continue
    columns = ["node_id", "type", "inv_elev", "max_depth", "pond_area", "ext_flow"]
    return pd.DataFrame(node_summary_data, columns=columns)

def _extract_highest_continuity_error(content):
    error_data = {}
    error_pattern = "Node\\s+([A-Za-z0-9\\-]+)\\s+\\(([\\d\\.]+)%\\)"
    for line in content:
        match = re.search(error_pattern, line)
        if match:
            node_name = match.group(1)
            error_value = float(match.group(2))
            error_data[node_name] = error_value
    return error_data

def _extract_node_depth_summary(content):
    depth_data = {}
    for line in content[7:]:
        parts = line.split()
        if len(parts) >= 6:
            try:
                node_name = parts[0]
                avg_depth = float(parts[2])
                max_depth = float(parts[3])
                max_hgl = float(parts[4])
                time_of_max = f"{parts[5]} {parts[6]}" if len(parts) > 6 else ""
                depth_data[node_name] = {"Avg_Depth": avg_depth, "Max_Depth": max_depth, "Max_HGL": max_hgl, "Time_of_Max": time_of_max}
            except ValueError:
                continue
    return depth_data

def _extract_node_inflow_summary(content):
    inflow_data = {}
    for line in content[8:]:
        parts = line.split()
        if len(parts) >= 8:
            try:
                node_name = parts[0]
                max_lateral_inflow = float(parts[2])
                max_total_inflow = float(parts[3])
                time_of_max = f"{parts[4]} {parts[5]}" if len(parts) > 5 else ""
                lateral_inflow_volume = float(parts[6])
                total_inflow_volume = float(parts[7])
                inflow_data[node_name] = {"Max_Lateral_Inflow": max_lateral_inflow, "Max_Total_Inflow": max_total_inflow,
                                          "Time_of_Max_Inflow": time_of_max, "Lateral_Inflow_Volume": lateral_inflow_volume,
                                          "Total_Inflow_Volume": total_inflow_volume}
            except ValueError:
                continue
    return inflow_data

def _extract_node_surcharge_summary(content):
    surcharge_data = {}
    for line in content[8:]:
        parts = line.split()
        if len(parts) >= 5:
            try:
                node_name = parts[0]
                hours_surcharged = float(parts[2])
                max_height_above_crown = float(parts[3])
                min_depth_below_rim = float(parts[4])
                surcharge_data[node_name] = {"Hours_Surcharged": hours_surcharged, "Max_Height_Above_Crown": max_height_above_crown, "Min_Depth_Below_Rim": min_depth_below_rim}
            except ValueError:
                continue
    return surcharge_data

def _extract_node_flooding_summary(content):
    flooding_data = {}
    for line in content[8:]:
        parts = line.split()
        if len(parts) >= 7:
            try:
                node_name = parts[0]
                hours_flooded = float(parts[1])
                max_flooding_rate = float(parts[2])
                time_of_max_flooding = f"{parts[3]} {parts[4]}" if len(parts) > 4 else ""
                total_flood_volume = float(parts[5])
                max_ponded_depth = float(parts[6])
                flooding_data[node_name] = {"Hours_Flooded": hours_flooded, "Max_Flooding_Rate": max_flooding_rate,
                                            "Time_of_Max_Flooding": time_of_max_flooding, "Total_Flood_Volume": total_flood_volume,
                                            "Max_Ponded_Depth": max_ponded_depth}
            except ValueError:
                continue
    return flooding_data

def _extract_outfall_loading_summary(content):
    outfall_data = {}
    for line in content[8:]:
        parts = line.split()
        if len(parts) == 5:
            try:
                node_name = parts[0]
                flow_freq = float(parts[1])
                avg_flow = float(parts[2])
                max_flow = float(parts[3])
                total_volume = float(parts[4])
                outfall_data[node_name] = {"Flow_Freq_Pcnt": flow_freq, "Avg_Flow_CFS": avg_flow,
                                           "Max_Flow_CFS": max_flow, "Total_Volume_gal": total_volume}
            except ValueError:
                continue
    return outfall_data

def _extract_coordinates(content):
    coordinates_data = {}
    start_marker = "[COORDINATES]"
    header_marker = ";;--------------"
    recording = False
    for line in content:
        if start_marker in line:
            recording = True
            continue
        elif recording and (header_marker in line or line.strip() == ""):
            continue
        elif recording:
            parts = line.split()
            if len(parts) == 3:
                try:
                    node_name = parts[0]
                    x_coord = float(parts[1])
                    y_coord = float(parts[2])
                    coordinates_data[node_name] = {"X_Coord": x_coord, "Y_Coord": y_coord}
                except ValueError:
                    continue
    return pd.DataFrame.from_dict(coordinates_data, orient='index')

def extract_node_data(folder_path: str) -> pd.DataFrame:
    """
    Extract and merge data from SWMM RPT and INP files into a single DataFrame.
    
    Args:
        folder_path (str): Path to folder containing SWMM.rpt and SWMM.inp files
        
    Returns:
        pd.DataFrame: Merged DataFrame containing all SWMM node data and coordinates
        
    Raises:
        FileNotFoundError: If either SWMM.rpt or SWMM.inp files are not found
    """
    # Construct file paths
    rpt_path = os.path.join(folder_path, "swmm.RPT")
    inp_path = os.path.join(folder_path, "SWMM.inp")
    
    # Read file contents
    with open(rpt_path, "r") as rpt_file:
        rpt_content = rpt_file.readlines()

    with open(inp_path, "r") as inp_file:
        inp_content = inp_file.readlines()

    # Extract base node summary and continuity errors
    node_summary_df = _extract_node_summary(rpt_content)
    continuity_errors = _extract_highest_continuity_error(rpt_content)
    node_summary_df["cont_err"] = node_summary_df["node_id"].map(continuity_errors).fillna(0.0)

    # Extract all summary sections
    summary_data = {
        "depth": _extract_node_depth_summary(rpt_content),
        "inflow": _extract_node_inflow_summary(rpt_content),
        "surcharge": _extract_node_surcharge_summary(rpt_content),
        "flooding": _extract_node_flooding_summary(rpt_content),
        "outfall": _extract_outfall_loading_summary(rpt_content)
    }

    # Map depth summary data
    node_summary_df["avg_depth"] = node_summary_df["node_id"].map(lambda x: summary_data["depth"].get(x, {}).get("Avg_Depth", 0.0))
    node_summary_df["max_depth"] = node_summary_df["node_id"].map(lambda x: summary_data["depth"].get(x, {}).get("Max_Depth", 0.0))
    node_summary_df["max_hgl"] = node_summary_df["node_id"].map(lambda x: summary_data["depth"].get(x, {}).get("Max_HGL", 0.0))
    node_summary_df["time_max"] = node_summary_df["node_id"].map(lambda x: summary_data["depth"].get(x, {}).get("Time_of_Max", ""))
    
    # Map inflow summary data
    node_summary_df["lat_flow"] = node_summary_df["node_id"].map(lambda x: summary_data["inflow"].get(x, {}).get("Max_Lateral_Inflow", 0.0))
    node_summary_df["tot_flow"] = node_summary_df["node_id"].map(lambda x: summary_data["inflow"].get(x, {}).get("Max_Total_Inflow", 0.0))
    node_summary_df["time_flow"] = node_summary_df["node_id"].map(lambda x: summary_data["inflow"].get(x, {}).get("Time_of_Max_Inflow", ""))
    node_summary_df["lat_vol"] = node_summary_df["node_id"].map(lambda x: summary_data["inflow"].get(x, {}).get("Lateral_Inflow_Volume", 0.0))
    node_summary_df["tot_vol"] = node_summary_df["node_id"].map(lambda x: summary_data["inflow"].get(x, {}).get("Total_Inflow_Volume", 0.0))

    # Map surcharge summary data
    node_summary_df["hrs_surch"] = node_summary_df["node_id"].map(lambda x: summary_data["surcharge"].get(x, {}).get("Hours_Surcharged", 0.0))
    node_summary_df["ht_crown"] = node_summary_df["node_id"].map(lambda x: summary_data["surcharge"].get(x, {}).get("Max_Height_Above_Crown", 0.0))
    node_summary_df["dpth_rim"] = node_summary_df["node_id"].map(lambda x: summary_data["surcharge"].get(x, {}).get("Min_Depth_Below_Rim", 0.0))

    # Map flooding summary data
    node_summary_df["hrs_flood"] = node_summary_df["node_id"].map(lambda x: summary_data["flooding"].get(x, {}).get("Hours_Flooded", 0.0))
    node_summary_df["fld_rate"] = node_summary_df["node_id"].map(lambda x: summary_data["flooding"].get(x, {}).get("Max_Flooding_Rate", 0.0))
    node_summary_df["time_fld"] = node_summary_df["node_id"].map(lambda x: summary_data["flooding"].get(x, {}).get("Time_of_Max_Flooding", ""))
    node_summary_df["fld_vol"] = node_summary_df["node_id"].map(lambda x: summary_data["flooding"].get(x, {}).get("Total_Flood_Volume", 0.0))
    node_summary_df["pond_dpth"] = node_summary_df["node_id"].map(lambda x: summary_data["flooding"].get(x, {}).get("Max_Ponded_Depth", 0.0))

    # Map outfall loading summary data
    node_summary_df["flow_freq"] = node_summary_df["node_id"].map(lambda x: summary_data["outfall"].get(x, {}).get("Flow_Freq_Pcnt", 0.0))
    node_summary_df["avg_flow"] = node_summary_df["node_id"].map(lambda x: summary_data["outfall"].get(x, {}).get("Avg_Flow_CFS", 0.0))
    node_summary_df["max_flow"] = node_summary_df["node_id"].map(lambda x: summary_data["outfall"].get(x, {}).get("Max_Flow_CFS", 0.0))
    node_summary_df["vol_gal"] = node_summary_df["node_id"].map(lambda x: summary_data["outfall"].get(x, {}).get("Total_Volume_gal", 0.0))

    # Extract and merge coordinates
    coordinates_df = _extract_coordinates(inp_content)
    merged_df = node_summary_df.merge(coordinates_df, left_on="node_id", right_index=True, how="left")
    
    return merged_df

# Example usage:
df_full = extract_node_data(r"R:\_anichols\Projects\_flo2d_postprocessor_tests\Detroit_Basin_Prop100y24h")
print(df_full)

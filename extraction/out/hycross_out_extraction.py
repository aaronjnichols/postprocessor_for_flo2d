import os
import re
import pandas as pd
from core.utilities import time_function
from core.constants import FPXS_ID, TIME_MAX_DISCHARGE, Q_MAX, VOL_ACFT, WSE_MAX, TIME, DISCHARGE

# Regular expression patterns
Q_MAX_PATTERN = re.compile(r'MAXIMUM DISCHARGE FROM CROSS SECTION\s+\d+\s+IS:\s+(\d+\.\d+)\s+CFS')
TIME_MAX_PATTERN = re.compile(r'AT TIME:\s+(\d+\.\d+)\s+HOURS')
VOL_PATTERN = re.compile(r'VOLUME OF DISCHARGE IS:\s+(\d+\.\d+)\s+AF')
HYDROGRAPH_PATTERN = re.compile(r'^\s*(\d+\.\d+)', re.MULTILINE)

def _extract_max_q_vol_time(file_lines):
    """
    Extract maximum discharge, time, and volume data from HYCROSS.OUT file content.
    
    Args:
        file_lines (str): Content of the HYCROSS.OUT file
        
    Returns:
        pd.DataFrame: DataFrame with FPXSEC ID, max discharge time, max discharge, and volume
    """
    q_max = re.findall(Q_MAX_PATTERN, file_lines)
    time_max = re.findall(TIME_MAX_PATTERN, file_lines)
    vol = re.findall(VOL_PATTERN, file_lines)

    data = {
        FPXS_ID: list(range(1, len(q_max) + 1)),
        TIME_MAX_DISCHARGE: time_max,
        Q_MAX: q_max,
        VOL_ACFT: vol
    }
    return pd.DataFrame.from_dict(data)


def _get_start_end_time(file_content):
    """
    Extract start and end times from hydrograph data in the file content.
    
    Args:
        file_content (str): Content of the HYCROSS.OUT file
        
    Returns:
        tuple: (start_time, end_time) or (None, None) if no times found
    """
    hydrograph_times = re.findall(HYDROGRAPH_PATTERN, file_content)

    if hydrograph_times:
        hydrograph_times = [float(t) for t in hydrograph_times]
        return min(hydrograph_times), max(hydrograph_times)
    else:
        return None, None
    

def _extract_max_wse(file_content, start_time, end_time):
    """
    Extract maximum water surface elevation for each section within the specified time range.
    
    Args:
        file_content (str): Content of the HYCROSS.OUT file
        start_time (float): Start time for analysis
        end_time (float): End time for analysis
        
    Returns:
        list: Maximum water surface elevation values for each section
    """
    wse_max_values = []
    wse = []

    for line in file_content.split('\n'):
        splt = line.split()

        try:
            if splt and len(splt) > 3 and float(splt[0]) == start_time:
                wse = [float(splt[3])]
            elif splt and len(splt) > 3 and start_time < float(splt[0]) < end_time:
                wse.append(float(splt[3]))
            elif splt and len(splt) > 3 and float(splt[0]) == end_time:
                wse_max_values.append(max(wse))
        except ValueError:
            continue

    return wse_max_values


@time_function
def extract_hycross_out(file_path):
    """
    Extract floodplain cross-section results from HYCROSS.OUT file.
    
    This function extracts maximum discharge, time, volume, and water surface 
    elevation data for floodplain cross-sections.
    
    Args:
        file_path (str): Path to the directory containing HYCROSS.OUT file
        
    Returns:
        pd.DataFrame: DataFrame with FPXSEC results including Q_MAX, TIME_MAX_DISCHARGE, 
                     VOL_ACFT, and WSE_MAX columns
    """
    with open(os.path.join(file_path, 'HYCROSS.OUT'), 'r') as file:
        file_content = file.read()
    start_time, end_time = _get_start_end_time(file_content)
    wse_max_values = _extract_max_wse(file_content, start_time, end_time)
    fpxsec_results = _extract_max_q_vol_time(file_content)

    if len(wse_max_values) == len(fpxsec_results):
        fpxsec_results[WSE_MAX] = wse_max_values

    return fpxsec_results


def extract_hycross_hydrograph_data(folder_path):
    """
    Extracts hydrograph data (time and discharge) from the HYCROSS.OUT file, integrating the maximum discharge
    at its correct time position and extracting the maximum water surface elevation.
    
    Args:
        folder_path (str): Path to the project folder containing HYCROSS.OUT file
        
    Returns:
        tuple: (hydrograph_data dict, max_wse_info dict)
        
    Raises:
        FileNotFoundError: If HYCROSS.OUT file is not found in the specified folder
    """
    file_path = os.path.join(folder_path, 'HYCROSS.OUT')
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"HYCROSS.OUT file not found at {file_path}")
        
    hydrograph_data = {}
    max_discharge_info = {}  # Store max discharge info for each section
    max_wse_info = {}  # Store max water surface elevation info for each section
    current_section = None  # Initialize the current_section variable
    current_wse = -float('inf')  # Initialize the current_wse variable

    with open(file_path, 'r') as file:
        for line in file:
            # Check for the line with maximum discharge information
            if 'THE MAXIMUM DISCHARGE FROM CROSS SECTION' in line:
                match = re.search(r'THE MAXIMUM DISCHARGE FROM CROSS SECTION\s*(\d+) IS:\s*([\d.]+) CFS AT TIME:\s*([\d.]+)', line)
                if match:
                    section = int(match.group(1))
                    max_discharge = float(match.group(2))
                    max_time = float(match.group(3))
                    max_discharge_info[section] = (max_time, max_discharge)
                continue

            # Check for the line with maximum water surface elevation information
            if 'MAXIMUM WATER SURFACE ELEVATION AT CROSS SECTION' in line:
                match = re.search(r'MAXIMUM WATER SURFACE ELEVATION AT CROSS SECTION\s*(\d+)\s*IS:\s*([\d.]+)', line)
                if match:
                    section = int(match.group(1))
                    max_wse = float(match.group(2))
                    max_wse_info[section] = max_wse
                continue

            # Check for the start of a hydrograph section
            if 'HYDROGRAPH AND FLOODPLAIN HYDRAULICS' in line:
                match = re.search(r'FOR CROSS SECTION NO:\s*(\d+)', line)
                if match:
                    current_section = int(match.group(1))
                    hydrograph_data[current_section] = []
                    current_wse = -float('inf')  # Reset for new section
                continue

            # Detect the start of the data (after the column headers)
            if 'TIME' in line and 'DISCHARGE' in line:
                continue  # Skip the header line

            # Extract data if in a data section
            if current_section is not None:
                try:
                    parts = line.split()
                    time = float(parts[0])
                    wse = float(parts[3])  # Extract WS ELEV
                    discharge = float(parts[5])
                    hydrograph_data[current_section].append((time, discharge))
                    if wse > current_wse:
                        current_wse = wse
                    max_wse_info[current_section] = current_wse
                except (IndexError, ValueError):
                    # Handle lines that do not contain valid data
                    continue

    # Convert lists to pandas DataFrames and integrate max discharge
    for section in hydrograph_data:
        df = pd.DataFrame(hydrograph_data[section], columns=[TIME, DISCHARGE])
        if section in max_discharge_info:
            df = _integrate_max_discharge_in_df(df, max_discharge_info[section])
        hydrograph_data[section] = df

    return hydrograph_data, max_wse_info


def _integrate_max_discharge_in_df(hydrograph_data, max_discharge_info):
    """
    Integrates the maximum discharge information into the DataFrame at its correct time position.
    
    Args:
        hydrograph_data (pd.DataFrame): DataFrame with TIME and DISCHARGE columns
        max_discharge_info (tuple): (max_time, max_discharge)
        
    Returns:
        pd.DataFrame: Updated DataFrame with max discharge integrated
    """
    max_time, max_discharge = max_discharge_info

    # Check if the max time already exists in the DataFrame
    if max_time in hydrograph_data[TIME].values:
        hydrograph_data.loc[hydrograph_data[TIME] == max_time, DISCHARGE] = max_discharge
    else:
        # Insert a new row for the maximum discharge
        new_row = pd.DataFrame({TIME: [max_time], DISCHARGE: [max_discharge]})
        hydrograph_data = pd.concat([hydrograph_data, new_row], ignore_index=True)
        hydrograph_data = hydrograph_data.sort_values(by=TIME).reset_index(drop=True)

    return hydrograph_data
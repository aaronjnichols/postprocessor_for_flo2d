import os
import pandas as pd
import re
from core.utilities import time_function
from core.constants import TIME, INFLOW, OUTFLOW, STRUCTURE_ID

def _parse_hydrograph_data(folder_path):
    """Parse hydrograph data from HYDROSTRUCT.OUT."""
    file_path = os.path.join(folder_path, 'HYDROSTRUCT.OUT')
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"HYDROSTRUCT.OUT file not found at {file_path}")
    
    hydrograph_data = {}
    current_structure = None
    current_data = []
    structure_header_re = re.compile(r'THE MAXIMUM DISCHARGE FOR:\s+(\S+)\s+')
    data_row_re = re.compile(r'^\s*(\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)')

    try:
        with open(file_path, 'r') as file:
            for line in file:
                header_match = structure_header_re.search(line)
                if header_match:
                    if current_structure and current_data:
                        df = pd.DataFrame(current_data, columns=[TIME, INFLOW, OUTFLOW])
                        hydrograph_data[current_structure] = df
                        current_data = []
                    current_structure = header_match.group(1)
                else:
                    data_match = data_row_re.search(line)
                    if data_match:
                        time, inflow, outflow = data_match.groups()
                        current_data.append([float(time), float(inflow), float(outflow)])
            if current_structure and current_data:
                df = pd.DataFrame(current_data, columns=[TIME, INFLOW, OUTFLOW])
                hydrograph_data[current_structure] = df

        if not hydrograph_data:
            raise ValueError(f"No hydrograph data found in {file_path}")

    except FileNotFoundError:
        raise
    except ValueError:
        raise  
    except Exception as e:
        raise RuntimeError(f"Error reading HYDROSTRUCT.OUT file: {e}") from e

    return hydrograph_data

def _extract_hydrostruct_peaks(folder_path):
    """Extract peak discharge and time to peak from HYDROSTRUCT.OUT."""
    file_path = os.path.join(folder_path, 'HYDROSTRUCT.OUT')
    peaks = {}
    with open(file_path, 'r') as file:
        for line in file:
            if 'THE MAXIMUM DISCHARGE FOR:' in line:
                parts = line.split()
                struct_idx = parts.index('FOR:') + 1
                structure_name = parts[struct_idx]
                is_idx = parts.index('IS:')
                peak_discharge = float(parts[is_idx + 1])
                at_idx = parts.index('AT', is_idx)
                time_of_peak = float(parts[at_idx + 2])
                peaks[structure_name] = {
                    'qpeak_cfs': peak_discharge,
                    'tpeak_hrs': time_of_peak,
                }

    df = pd.DataFrame.from_dict(peaks, orient='index').reset_index()
    df.rename(columns={'index': STRUCTURE_ID}, inplace=True)
    return df


@time_function
def extract_hydrostruct_out(folder_path):
    """
    Extract hydraulic structure data from HYDROSTRUCT.OUT file.
    
    This function extracts both hydrograph time series data and peak flow statistics
    for hydraulic structures.
    
    Args:
        folder_path (str): Path to the directory containing HYDROSTRUCT.OUT file
        
    Returns:
        dict: Dictionary containing:
            - 'hydrographs': Dict of DataFrames with time series data for each structure
            - 'peaks': DataFrame with peak discharge and timing information
            
    Raises:
        FileNotFoundError: If HYDROSTRUCT.OUT file is not found
        ValueError: If no data found in file
        RuntimeError: If error reading file
    """
    file_path = os.path.join(folder_path, 'HYDROSTRUCT.OUT')
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"HYDROSTRUCT.OUT file not found at {file_path}")
    
    # Extract both hydrographs and peaks
    hydrographs = _parse_hydrograph_data(folder_path)
    peaks = _extract_hydrostruct_peaks(folder_path)
    
    return {
        'hydrographs': hydrographs,
        'peaks': peaks
    }

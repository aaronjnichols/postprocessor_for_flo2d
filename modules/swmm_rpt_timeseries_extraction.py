import os
import re
import pandas as pd
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import LineChart, Reference

def parse_swmm_links_to_dataframe(file_path):
    """
    Parses SWMM report file to extract time series data for all links into a single dataframe.
    
    Parameters:
        file_path (str): Path to the SWMM report file.

    Returns:
        pd.DataFrame: A dataframe containing a 'Time' column and discharge data for each link.
    """
    import re
    import pandas as pd
    from collections import defaultdict

    # Define regex patterns
    link_pattern = re.compile(r"<<< Link (.*?) >>>")
    data_pattern = re.compile(r"(\w{3}-\d{2}-\d{4})\s+(\d{2}:\d{2}:\d{2})\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)")

    # Load the file content
    with open(file_path, 'r') as file:
        rpt_content = file.readlines()

    # Initialize containers
    time_series_dict = {}
    common_times = []

    current_link = None

    # Parse the file
    for line in rpt_content:
        # Check for link header
        link_match = link_pattern.search(line)
        if link_match:
            current_link = link_match.group(1)
            if current_link not in time_series_dict:
                time_series_dict[current_link] = []
            continue

        # Extract time series data for the current link
        data_match = data_pattern.search(line)
        if data_match and current_link:
            date, time, flow, velocity, depth, percent_full = data_match.groups()
            datetime = f"{date} {time}"
            flow = float(flow)

            if not common_times or datetime not in common_times:
                common_times.append(datetime)

            time_series_dict[current_link].append(flow)

    # Adjust for missing data
    flows_dict = defaultdict(lambda: {link: None for link in time_series_dict.keys()})
    for link, flows in time_series_dict.items():
        for i, datetime in enumerate(common_times[:len(flows)]):
            flows_dict[datetime][link] = flows[i]

    # Create the dataframe
    df_combined = pd.DataFrame.from_dict(flows_dict, orient="index")
    df_combined.index.name = "Time"
    df_combined.reset_index(inplace=True)

    return df_combined

def parse_swmm_nodes_to_dataframe(file_path):
    """
    Parses SWMM report file to extract time series data for all nodes into a single dataframe.

    Parameters:
        file_path (str): Path to the SWMM report file.

    Returns:
        pd.DataFrame: A dataframe containing a 'Time' column and inflow data for each node.
    """
    import re
    import pandas as pd
    from collections import defaultdict

    # Define regex patterns
    node_pattern = re.compile(r"<<< Node (.*?) >>>")
    data_pattern = re.compile(r"(\w{3}-\d{2}-\d{4})\s+(\d{2}:\d{2}:\d{2})\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)")

    # Load the file content
    with open(file_path, 'r') as file:
        rpt_content = file.readlines()

    # Initialize containers
    time_series_dict = {}
    common_times = []

    current_node = None

    # Parse the file
    for line in rpt_content:
        # Check for node header
        node_match = node_pattern.search(line)
        if node_match:
            current_node = node_match.group(1)
            if current_node not in time_series_dict:
                time_series_dict[current_node] = []
            continue

        # Extract time series data for the current node
        data_match = data_pattern.search(line)
        if data_match and current_node:
            date, time, inflow, flooding, depth, head = data_match.groups()
            datetime = pd.to_datetime(f"{date} {time}", format='%b-%d-%Y %H:%M:%S')
            inflow = float(inflow)

            if not common_times or datetime not in common_times:
                common_times.append(datetime)

            time_series_dict[current_node].append(inflow)

    # Adjust for missing data
    flows_dict = defaultdict(lambda: {node: None for node in time_series_dict.keys()})
    for node, inflows in time_series_dict.items():
        for i, datetime in enumerate(common_times[:len(inflows)]):
            flows_dict[datetime][node] = inflows[i]

    # Create the dataframe
    df_combined = pd.DataFrame.from_dict(flows_dict, orient="index")
    df_combined.index.name = "Time"
    df_combined.reset_index(inplace=True)

    return df_combined

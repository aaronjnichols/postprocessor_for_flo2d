import os
import logging
import pandas as pd
from core.utilities import time_function
from core.constants import STAGE, FLOW
from core.path_resolver import resolve_model_file_path

@time_function
def extract_swmmflort_dat(file_path):
    """
    Extracts rating tables from a SWMMFLORT.DAT file.

    Args:
    file_path (str): Path to the directory containing SWMMFLORT.DAT file.

    Returns:
    list: A list of dictionaries, each containing table name and data.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    file_path = resolve_model_file_path(file_path, "SWMMFLORT.DAT")
    rating_tables = []
    current_table = None

    try:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split()
                
                if line.startswith('D') and len(parts) >= 3:
                    if current_table:
                        rating_tables.append(current_table)
                    current_table = {"Table": parts[2], "Data": []}
                
                elif line.startswith('N') and len(parts) == 3 and current_table:
                    try:
                        stage = float(parts[1])
                        discharge = float(parts[2])
                        current_table["Data"].append({STAGE: stage, FLOW: discharge})
                    except ValueError:
                        logger.warning("Could not convert SWMMFLORT.DAT values to float: %s", parts)

        if current_table:
            rating_tables.append(current_table)

        # Convert data to pandas DataFrame
        for table in rating_tables:
            table["Data"] = pd.DataFrame(table["Data"])

    except Exception as e:
        logger.error("An error occurred while processing SWMMFLORT.DAT: %s", e)
        return []

    return rating_tables

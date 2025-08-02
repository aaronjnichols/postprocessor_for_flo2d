import os
import pandas as pd
from core.utilities import time_function

@time_function
def extract_chanbank_dat(path):
    """
    Extract channel bank relationships from CHANBANK.DAT.
    
    Args:
        path (str): Path to the FLO-2D project directory.
        
    Returns:
        pd.DataFrame: DataFrame with columns ['xsec_id', 'left_bank', 'right_bank'].
                     Returns empty DataFrame if file doesn't exist or on error.
    """
    file_path = os.path.join(path, 'CHANBANK.DAT')
    
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=['xsec_id', 'left_bank', 'right_bank'])
    
    try:
        data = []
        with open(file_path, 'r') as file:
            for i, line in enumerate(file, 1):
                line = line.strip()
                if line:
                    try:
                        left_bank, right_bank = map(int, line.split())
                        data.append({
                            'xsec_id': i,
                            'left_bank': left_bank,
                            'right_bank': right_bank
                        })
                    except ValueError:
                        # Skip malformed lines
                        continue
        
        return pd.DataFrame(data)
        
    except Exception as e:
        print(f"Error reading CHANBANK.DAT: {e}")
        return pd.DataFrame(columns=['xsec_id', 'left_bank', 'right_bank'])
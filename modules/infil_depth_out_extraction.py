import os
from .extraction_utils import read_file_with_line_number


def extract_infil_depth_out(path):
    file_path = os.path.join(path, 'INFIL_DEPTH.OUT')
    df = read_file_with_line_number(file_path, ['x', 'y', 'infil_depth', 'infil_stop'], skiprows=1)
    return df

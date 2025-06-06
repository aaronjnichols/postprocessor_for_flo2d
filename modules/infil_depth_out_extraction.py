import os
from .extraction_utils import read_file_with_line_number
from .constants import X_COORD, Y_COORD, INFIL_DEPTH


def extract_infil_depth_out(path):
    file_path = os.path.join(path, 'INFIL_DEPTH.OUT')
    df = read_file_with_line_number(file_path, [X_COORD, Y_COORD, INFIL_DEPTH, 'infil_stop'], skiprows=1)
    return df

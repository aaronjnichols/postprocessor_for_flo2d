import os
from .extraction_utils import read_file_with_line_number
from .constants import X_COORD, Y_COORD, TOPO_ELEVATION


def extract_topo(path):
    file_path = os.path.join(path, 'TOPO.DAT')
    return read_file_with_line_number(file_path, [X_COORD, Y_COORD, TOPO_ELEVATION])

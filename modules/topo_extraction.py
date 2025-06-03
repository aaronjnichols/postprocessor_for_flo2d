import os
from .extraction_utils import read_file_with_line_number


def extract_topo(path):
    file_path = os.path.join(path, 'TOPO.DAT')
    return read_file_with_line_number(file_path, ['x', 'y', 'topo'])

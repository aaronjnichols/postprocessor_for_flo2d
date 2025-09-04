"""Extract link information from SWMM ``*.rpt`` files.

This module is now a thin wrapper that delegates to common link parsing
helpers implemented in ``swmm_rpt_base`` to avoid duplication and ensure
consistent behavior with node extraction.
"""

from core.utilities import time_function
from .swmm_rpt_base import _extract_links_rpt


@time_function
def extract_swmmlinks_rpt(folder_path):
    """Extract link related data from a SWMM ``*.rpt`` file.

    Delegates to the shared base implementation.
    """

    return _extract_links_rpt(folder_path)


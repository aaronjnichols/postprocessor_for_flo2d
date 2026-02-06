"""
FLO-2D Postprocessor QGIS Plugin - Hydrograph data handler.

Resolves the FLO-2D project folder from a layer source path, parses
HYCROSS.OUT (with caching), and opens a HydrographDialog popup.
"""

import os
import sys
from contextlib import contextmanager

from qgis.utils import iface


# ---------------------------------------------------------------------------
# Module-level cache: project_folder -> (hydrograph_data, max_wse_info)
# ---------------------------------------------------------------------------
_hydrograph_cache = {}


# ---------------------------------------------------------------------------
# sys.path / sys.modules context manager
# ---------------------------------------------------------------------------

@contextmanager
def _project_import_context():
    """Temporarily put the postprocessor project root on *sys.path* and evict
    QGIS's ``processing`` module so our own ``extraction`` / ``core`` packages
    resolve correctly.  Restores the original state on exit.
    """
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(plugin_dir)

    inserted = False
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        inserted = True

    # Evict QGIS processing modules
    saved = {}
    for key in list(sys.modules):
        if key == "processing" or key.startswith("processing."):
            saved[key] = sys.modules.pop(key)

    try:
        yield project_root
    finally:
        # Restore QGIS processing modules
        sys.modules.update(saved)
        if inserted:
            try:
                sys.path.remove(project_root)
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Core handler
# ---------------------------------------------------------------------------

def show_hydrograph_for_feature(layer_source, fpxs_id, vol_acft):
    """Open the hydrograph dialog for a given cross-section feature.

    Args:
        layer_source (str): File-system path of the fpxsec layer source
            (e.g. ``…/flo2d_shp/fpxsec.gpkg``).
        fpxs_id (int|str): Floodplain cross-section ID.
        vol_acft (float|str): Volume in acre-feet (from feature attribute).
    """
    fpxs_id = int(fpxs_id)
    try:
        vol_acft = float(vol_acft)
    except (TypeError, ValueError):
        vol_acft = None

    # Strip GeoPackage "|layername=..." suffix if present
    if "|" in layer_source:
        layer_source = layer_source.split("|")[0]

    # Resolve project folder: layer_source sits inside <project>/flo2d_shp/
    project_folder = os.path.dirname(os.path.dirname(layer_source))

    # Retrieve (or parse) hydrograph data
    if project_folder not in _hydrograph_cache:
        with _project_import_context():
            from extraction.out.hycross_out_extraction import (
                extract_hycross_hydrograph_data,
            )
            hydrograph_data, max_wse_info = extract_hycross_hydrograph_data(
                project_folder
            )
        _hydrograph_cache[project_folder] = (hydrograph_data, max_wse_info)

    hydrograph_data, max_wse_info = _hydrograph_cache[project_folder]

    if fpxs_id not in hydrograph_data:
        from qgis.PyQt.QtWidgets import QMessageBox

        QMessageBox.warning(
            iface.mainWindow(),
            "Hydrograph Not Found",
            f"No hydrograph data for cross-section {fpxs_id}.\n"
            "Check that HYCROSS.OUT is present and contains data for this section.",
        )
        return

    df = hydrograph_data[fpxs_id]
    max_wse = max_wse_info.get(fpxs_id)

    # Derive stats from the hydrograph DataFrame
    discharge_col = df.columns[1]
    time_col = df.columns[0]
    q_max = float(df[discharge_col].max())
    time_max_discharge = float(
        df.loc[df[discharge_col] == q_max, time_col].iloc[0]
    )

    stats = {
        "q_max": q_max,
        "time_max_discharge": time_max_discharge,
        "vol_acft": vol_acft,
        "wse_max": max_wse,
    }

    # Import dialog here to keep matplotlib import lazy
    from .hydrograph_dialog import HydrographDialog

    dlg = HydrographDialog(fpxs_id, df, stats, parent=iface.mainWindow())
    dlg.show()


def clear_hydrograph_cache():
    """Clear cached HYCROSS.OUT data."""
    _hydrograph_cache.clear()

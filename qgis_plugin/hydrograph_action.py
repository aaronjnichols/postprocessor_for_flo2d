"""
FLO-2D Postprocessor QGIS Plugin - Feature data handler.

Resolves the FLO-2D project folder from a layer source path, extracts
time-series data (with caching), and opens an interactive popup dialog
for floodplain cross sections, hydraulic structures, and SWMM features.
"""

import os
import sys
from contextlib import contextmanager

from qgis.utils import iface


# ---------------------------------------------------------------------------
# Module-level cache: keyed by (project_folder, feature_type)
# ---------------------------------------------------------------------------
_data_cache = {}


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
# Helpers
# ---------------------------------------------------------------------------

def _resolve_project_folder(layer_source):
    """Resolve the FLO-2D project folder from a layer source path.

    Layer sources sit inside ``<project>/flo2d_shp/``.  Strips any
    GeoPackage ``|layername=...`` suffix first.
    """
    if "|" in layer_source:
        layer_source = layer_source.split("|")[0]
    return os.path.dirname(os.path.dirname(layer_source))


def _fmt(value, decimals=2):
    """Format a numeric value, returning 'N/A' for non-numeric."""
    if isinstance(value, (int, float)):
        return f"{value:.{decimals}f}"
    return "N/A"


def _warn(title, message):
    """Show a warning in the QGIS message bar."""
    iface.messageBar().pushWarning(title, message)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def show_popup_for_feature(feature_type, layer_source, feature):
    """Route to the correct handler based on *feature_type*."""
    handlers = {
        "fpxsec": _show_fpxsec_popup,
        "hydraulic_structure": _show_hydrostruct_popup,
        "swmm_junction": _show_swmm_junction_popup,
        "swmm_outfall": _show_swmm_outfall_popup,
        "swmm_conduit": _show_swmm_conduit_popup,
    }
    handler = handlers.get(feature_type)
    if handler is None:
        _warn("Inspect Feature", f"Unsupported feature type: {feature_type}")
        return
    handler(layer_source, feature)


# ---------------------------------------------------------------------------
# Floodplain cross section
# ---------------------------------------------------------------------------

def _show_fpxsec_popup(layer_source, feature):
    project_folder = _resolve_project_folder(layer_source)
    cache_key = (project_folder, "fpxsec")

    if cache_key not in _data_cache:
        with _project_import_context():
            from extraction.out.hycross_out_extraction import (
                extract_hycross_hydrograph_data,
            )
            try:
                hydrograph_data, max_wse_info = extract_hycross_hydrograph_data(
                    project_folder
                )
            except FileNotFoundError:
                _warn("Inspect Feature",
                      "HYCROSS.OUT not found in the project folder.")
                return
        _data_cache[cache_key] = (hydrograph_data, max_wse_info)

    hydrograph_data, max_wse_info = _data_cache[cache_key]

    fpxs_id = int(feature["fpxs_id"])
    if fpxs_id not in hydrograph_data:
        _warn("Inspect Feature",
              f"No hydrograph data for cross-section {fpxs_id}.")
        return

    df = hydrograph_data[fpxs_id]
    max_wse = max_wse_info.get(fpxs_id)

    time_col, discharge_col = df.columns[0], df.columns[1]
    q_max = float(df[discharge_col].max())
    time_max = float(df.loc[df[discharge_col] == q_max, time_col].iloc[0])

    field_names = [f.name() for f in feature.fields()]
    vol_acft = feature["vol_acft"] if "vol_acft" in field_names else None
    try:
        vol_acft = float(vol_acft)
    except (TypeError, ValueError):
        vol_acft = None

    series = [{
        'x': df[time_col].values,
        'y': df[discharge_col].values,
        'label': 'Discharge (cfs)',
        'color': 'blue',
    }]
    stats = [
        ("Peak Q (cfs):", _fmt(q_max)),
        ("Time to Peak (hr):", _fmt(time_max)),
        ("Volume (ac-ft):", _fmt(vol_acft)),
        ("Max WSE (ft):", _fmt(max_wse)),
    ]

    _open_dialog(f"Hydrograph \u2014 Cross Section {fpxs_id}", series, stats)


# ---------------------------------------------------------------------------
# Hydraulic structure
# ---------------------------------------------------------------------------

def _show_hydrostruct_popup(layer_source, feature):
    project_folder = _resolve_project_folder(layer_source)
    cache_key = (project_folder, "hydraulic_structure")

    if cache_key not in _data_cache:
        with _project_import_context():
            from extraction.out.hydrostruct_out_extraction import (
                extract_hydrostruct_out,
            )
            try:
                data = extract_hydrostruct_out(project_folder)
            except FileNotFoundError:
                _warn("Inspect Feature",
                      "HYDROSTRUCT.OUT not found in the project folder.")
                return
        _data_cache[cache_key] = data

    data = _data_cache[cache_key]
    hydrographs = data.get("hydrographs", {})

    struct_id = str(feature["structure_id"])
    if struct_id not in hydrographs:
        _warn("Inspect Feature",
              f"No hydrograph data for structure '{struct_id}'.")
        return

    df = hydrographs[struct_id]
    # Columns: time, inflow, outflow
    time_col = df.columns[0]
    inflow_col = df.columns[1]
    outflow_col = df.columns[2]

    peak_inflow = float(df[inflow_col].max())
    time_peak_in = float(df.loc[df[inflow_col] == peak_inflow, time_col].iloc[0])
    peak_outflow = float(df[outflow_col].max())
    time_peak_out = float(df.loc[df[outflow_col] == peak_outflow, time_col].iloc[0])

    series = [
        {
            'x': df[time_col].values,
            'y': df[inflow_col].values,
            'label': 'Inflow (cfs)',
            'color': 'blue',
        },
        {
            'x': df[time_col].values,
            'y': df[outflow_col].values,
            'label': 'Outflow (cfs)',
            'color': 'red',
        },
    ]
    stats = [
        ("Peak Inflow (cfs):", _fmt(peak_inflow)),
        ("Time to Peak In (hr):", _fmt(time_peak_in)),
        ("Peak Outflow (cfs):", _fmt(peak_outflow)),
        ("Time to Peak Out (hr):", _fmt(time_peak_out)),
    ]

    _open_dialog(f"Hydrograph \u2014 Structure {struct_id}", series, stats)


# ---------------------------------------------------------------------------
# SWMM Junction
# ---------------------------------------------------------------------------

def _show_swmm_junction_popup(layer_source, feature):
    project_folder = _resolve_project_folder(layer_source)
    cache_key = (project_folder, "swmm_junction")

    if cache_key not in _data_cache:
        with _project_import_context():
            from extraction.out.swmm_junctions_rpt import (
                extract_swmm_junctions_rpt,
            )
            try:
                data = extract_swmm_junctions_rpt(project_folder)
            except FileNotFoundError:
                _warn("Inspect Feature",
                      "No SWMM .rpt file found in the project folder.")
                return
        _data_cache[cache_key] = data

    data = _data_cache[cache_key]
    node_ts = data.get("node_time_series")
    merged = data.get("merged_results")

    name = str(feature["name"])

    # Time-series column for this junction
    if node_ts is None or node_ts.empty or name not in node_ts.columns:
        _warn("Inspect Feature",
              f"No time-series data for junction '{name}'.")
        return

    series = [{
        'x': node_ts["time"].values,
        'y': node_ts[name].values,
        'label': 'Inflow (cfs)',
        'color': 'blue',
    }]

    # Build stats from merged_results
    stats = []
    if merged is not None and not merged.empty:
        row = merged.loc[merged["node_id"] == name]
        if not row.empty:
            row = row.iloc[0]
            _add_stat(stats, "Peak Inflow (cfs):", row, "tot_inflw")
            _add_stat(stats, "Time of Peak:", row, "t_tot_inflw")
            _add_stat(stats, "Max HGL (ft):", row, "Max_HGL")
            _add_stat(stats, "Flood Vol (MG):", row, "Total_Flood_Volume")

    _open_dialog(f"Junction \u2014 {name}", series, stats)


# ---------------------------------------------------------------------------
# SWMM Outfall
# ---------------------------------------------------------------------------

def _show_swmm_outfall_popup(layer_source, feature):
    project_folder = _resolve_project_folder(layer_source)
    cache_key = (project_folder, "swmm_outfall")

    if cache_key not in _data_cache:
        with _project_import_context():
            from extraction.out.swmm_outfalls_rpt import (
                extract_swmm_outfalls_rpt,
            )
            try:
                data = extract_swmm_outfalls_rpt(project_folder)
            except FileNotFoundError:
                _warn("Inspect Feature",
                      "No SWMM .rpt file found in the project folder.")
                return
        _data_cache[cache_key] = data

    data = _data_cache[cache_key]
    outfall_ts = data.get("outfall_time_series")
    outfall_loading = data.get("outfall_loading", {})

    name = str(feature["name"])

    if outfall_ts is None or outfall_ts.empty or name not in outfall_ts.columns:
        _warn("Inspect Feature",
              f"No time-series data for outfall '{name}'.")
        return

    series = [{
        'x': outfall_ts["time"].values,
        'y': outfall_ts[name].values,
        'label': 'Discharge (cfs)',
        'color': 'blue',
    }]

    stats = []
    loading = outfall_loading.get(name, {})
    if loading:
        stats.append(("Max Flow (cfs):", _fmt(loading.get("Max_Flow_CFS"))))
        stats.append(("Avg Flow (cfs):", _fmt(loading.get("Avg_Flow_CFS"))))
        stats.append(("Total Vol (MG):", _fmt(loading.get("Total_Volume_MG"))))
        stats.append(("Flow Freq (%):", _fmt(loading.get("Flow_Freq_Pcnt"))))

    _open_dialog(f"Outfall \u2014 {name}", series, stats)


# ---------------------------------------------------------------------------
# SWMM Conduit
# ---------------------------------------------------------------------------

def _show_swmm_conduit_popup(layer_source, feature):
    project_folder = _resolve_project_folder(layer_source)
    cache_key = (project_folder, "swmm_conduit")

    if cache_key not in _data_cache:
        with _project_import_context():
            from extraction.out.swmm_links_rpt import extract_swmmlinks_rpt
            try:
                data = extract_swmmlinks_rpt(project_folder)
            except FileNotFoundError:
                _warn("Inspect Feature",
                      "No SWMM .rpt file found in the project folder.")
                return
        _data_cache[cache_key] = data

    data = _data_cache[cache_key]
    link_ts = data.get("link_time_series")
    merged = data.get("merged_results")

    name = str(feature["name"])

    if link_ts is None or link_ts.empty or name not in link_ts.columns:
        _warn("Inspect Feature",
              f"No time-series data for conduit '{name}'.")
        return

    series = [{
        'x': link_ts["time"].values,
        'y': link_ts[name].values,
        'label': 'Flow (cfs)',
        'color': 'blue',
    }]

    stats = []
    if merged is not None and not merged.empty:
        row = merged.loc[merged["link_id"] == name]
        if not row.empty:
            row = row.iloc[0]
            _add_stat(stats, "Max Flow (cfs):", row, "max_flow")
            _add_stat(stats, "Max Velocity:", row, "max_vel")
            _add_stat(stats, "Flow Ratio:", row, "flow_ratio")
            _add_stat(stats, "Depth Ratio:", row, "depth_rat")

    _open_dialog(f"Conduit \u2014 {name}", series, stats)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _add_stat(stats_list, label, row, column):
    """Append a (label, formatted_value) tuple if the column exists."""
    if column in row.index:
        stats_list.append((label, _fmt(row[column])))


def _open_dialog(title, series, stats):
    """Import and open the dialog (keeps matplotlib import lazy)."""
    from .hydrograph_dialog import HydrographDialog
    dlg = HydrographDialog(title, series, stats, parent=iface.mainWindow())
    dlg.show()


def clear_data_cache():
    """Clear all cached extraction data."""
    _data_cache.clear()

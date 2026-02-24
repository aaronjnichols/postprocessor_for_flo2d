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
from .project_root import ensure_project_root_on_path


# ---------------------------------------------------------------------------
# Module-level cache: keyed by (project_folder, feature_type)
# ---------------------------------------------------------------------------
_data_cache = {}
_HYDROSTRUCT_ID_FIELDS = ("structure_id", "structure_")
_open_dialog_instances = []

_SWMM_NODE_METRICS = [
    {
        "id": "total_inflow",
        "label": "Inflow (cfs)",
        "color": "blue",
        "default_on": True,
    },
    {
        "id": "flooding",
        "label": "Flooding (cfs)",
        "color": "orange",
        "default_on": False,
    },
    {
        "id": "depth",
        "label": "Depth (ft)",
        "color": "green",
        "default_on": False,
    },
    {
        "id": "head",
        "label": "Head (ft)",
        "color": "purple",
        "default_on": False,
    },
]

_SWMM_LINK_METRICS = [
    {
        "id": "flow",
        "label": "Flow (cfs)",
        "color": "blue",
        "default_on": True,
    },
    {
        "id": "velocity",
        "label": "Velocity (ft/s)",
        "color": "red",
        "default_on": False,
    },
    {
        "id": "depth",
        "label": "Depth (ft)",
        "color": "green",
        "default_on": False,
    },
    {
        "id": "capacity",
        "label": "Percent Full (%)",
        "color": "orange",
        "default_on": False,
    },
]

_SWMM_NODE_LABEL = "Inflow (cfs)"
_SWMM_OUTFALL_LABEL = "Discharge (cfs)"


# ---------------------------------------------------------------------------
# sys.path / sys.modules context manager
# ---------------------------------------------------------------------------

@contextmanager
def _project_import_context():
    """Temporarily put the postprocessor project root on *sys.path* and evict
    QGIS's ``processing`` module so our own ``extraction`` / ``core`` packages
    resolve correctly.  Restores the original state on exit.
    """
    project_root, inserted = ensure_project_root_on_path(__file__)
    if project_root is None:
        raise ImportError(
            "Unable to locate FLO-2D postprocessor project root. "
            "Re-run scripts/install_qgis_plugin.bat and restart QGIS."
        )

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

    Layer sources sit inside ``<project>/flo2d_shp/`` or
    ``<project>/FLO2D_SHP/``.  Strips any GeoPackage
    ``|layername=...`` suffix first.
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


def _get_feature_value_by_aliases(feature, aliases):
    """Return the first non-empty feature value for any field alias."""
    field_lookup = {field.name().lower(): field.name() for field in feature.fields()}
    for alias in aliases:
        actual_name = field_lookup.get(alias.lower())
        if actual_name is None:
            continue
        value = feature[actual_name]
        if value is None:
            continue
        value_text = str(value).strip()
        if value_text:
            return value_text
    return None


def _build_series_from_dataframe(df, x_col, specs):
    """Build plot-ready series list from one DataFrame and series specs."""
    if df is None or df.empty or x_col not in df.columns:
        return []

    series = []
    for spec in specs:
        col = spec.get("column")
        if not col or col not in df.columns:
            continue
        series.append(
            {
                "id": spec.get("id", col),
                "x": df[x_col].values,
                "y": df[col].values,
                "label": spec.get("label", col),
                "color": spec.get("color", ""),
                "default_on": bool(spec.get("default_on", True)),
            }
        )
    return series


def _build_swmm_multi_series(metric_tables, feature_name, metric_specs):
    """Build plot-ready series from SWMM per-metric wide time-series tables."""
    if not metric_tables:
        return []

    series = []
    for spec in metric_specs:
        metric_id = spec["id"]
        ts_df = metric_tables.get(metric_id)
        if ts_df is None or ts_df.empty:
            continue
        if "time" not in ts_df.columns:
            continue
        feature_col = _resolve_timeseries_column(ts_df, feature_name)
        if feature_col is None:
            continue
        series.append(
            {
                "id": metric_id,
                "x": ts_df["time"].values,
                "y": ts_df[feature_col].values,
                "label": spec["label"],
                "color": spec["color"],
                "default_on": bool(spec.get("default_on", False)),
            }
        )
    return series


def _resolve_timeseries_column(df, feature_name):
    """Resolve feature_name to a DataFrame column with tolerant matching."""
    if df is None or df.empty:
        return None
    if feature_name in df.columns:
        return feature_name

    target = str(feature_name).strip().upper()
    for col in df.columns:
        if str(col).strip().upper() == target:
            return col
    return None


def _column_to_label(column_name):
    """Convert internal column names to user-friendly plot labels."""
    label_map = {
        "flow_width": "Flow Width (ft)",
        "ave_depth": "Avg Depth (ft)",
        "wse": "Water Surface Elev. (ft)",
        "velocity": "Velocity (ft/s)",
        "metric_3": "Metric 3",
        "metric_4": "Metric 4",
        "metric_5": "Metric 5",
        "metric_6": "Metric 6",
    }
    if column_name in label_map:
        return label_map[column_name]
    return column_name.replace("_", " ").title()


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
    try:
        handler(layer_source, feature)
    except ImportError as exc:
        _warn("Inspect Feature", str(exc))


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

    time_col = "time" if "time" in df.columns else df.columns[0]
    discharge_col = "discharge" if "discharge" in df.columns else df.columns[1]
    wse_col = "wse" if "wse" in df.columns else None
    flow_width_col = "flow_width" if "flow_width" in df.columns else None
    ave_depth_col = "ave_depth" if "ave_depth" in df.columns else None
    velocity_col = "velocity" if "velocity" in df.columns else None
    q_max = float(df[discharge_col].max())
    time_max = float(df.loc[df[discharge_col] == q_max, time_col].iloc[0])

    field_names = [f.name() for f in feature.fields()]
    vol_acft = feature["vol_acft"] if "vol_acft" in field_names else None
    try:
        vol_acft = float(vol_acft)
    except (TypeError, ValueError):
        vol_acft = None

    series_specs = [
        {
            "id": "discharge",
            "column": discharge_col,
            "label": "Discharge (cfs)",
            "color": "blue",
            "default_on": True,
        }
    ]
    if wse_col is not None:
        series_specs.append(
            {
                "id": "wse",
                "column": wse_col,
                "label": "Water Surface Elev. (ft)",
                "color": "green",
                "default_on": False,
            }
        )
    if flow_width_col is not None:
        series_specs.append(
            {
                "id": "flow_width",
                "column": flow_width_col,
                "label": "Flow Width (ft)",
                "color": "orange",
                "default_on": False,
            }
        )
    if ave_depth_col is not None:
        series_specs.append(
            {
                "id": "ave_depth",
                "column": ave_depth_col,
                "label": "Avg Depth (ft)",
                "color": "red",
                "default_on": False,
            }
        )
    if velocity_col is not None:
        series_specs.append(
            {
                "id": "velocity",
                "column": velocity_col,
                "label": "Velocity (ft/s)",
                "color": "purple",
                "default_on": False,
            }
        )
    series = _build_series_from_dataframe(df, time_col, series_specs)
    if not series:
        _warn("Inspect Feature", f"No plottable time-series data for cross-section {fpxs_id}.")
        return
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

    struct_id = _get_feature_value_by_aliases(feature, _HYDROSTRUCT_ID_FIELDS)
    if struct_id is None:
        _warn(
            "Inspect Feature",
            "Hydraulic structure layer is missing a structure ID field.",
        )
        return

    if struct_id not in hydrographs:
        _warn("Inspect Feature",
              f"No hydrograph data for structure '{struct_id}'.")
        return

    df = hydrographs[struct_id]
    if df is None or df.empty:
        _warn("Inspect Feature", f"No hydrograph data for structure '{struct_id}'.")
        return

    time_col = "time" if "time" in df.columns else df.columns[0]
    inflow_col = "inflow" if "inflow" in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
    outflow_col = "outflow" if "outflow" in df.columns else (df.columns[2] if len(df.columns) > 2 else None)

    stats = []
    series_specs = []
    if inflow_col is not None and inflow_col in df.columns:
        peak_inflow = float(df[inflow_col].max())
        time_peak_in = float(df.loc[df[inflow_col] == peak_inflow, time_col].iloc[0])
        stats.append(("Peak Inflow (cfs):", _fmt(peak_inflow)))
        stats.append(("Time to Peak In (hr):", _fmt(time_peak_in)))
        series_specs.append(
            {
                "id": "inflow",
                "column": inflow_col,
                "label": "Inflow (cfs)",
                "color": "blue",
                "default_on": True,
            }
        )

    if outflow_col is not None and outflow_col in df.columns:
        outflow_abs = df[outflow_col].abs()
        peak_outflow = float(outflow_abs.max())
        time_peak_out = float(df.loc[outflow_abs == peak_outflow, time_col].iloc[0])
        stats.append(("Peak Outflow (cfs):", _fmt(peak_outflow)))
        stats.append(("Time to Peak Out (hr):", _fmt(time_peak_out)))
        series_specs.append(
            {
                "id": "outflow",
                "column": outflow_col,
                "label": "Outflow (cfs)",
                "color": "red",
                "default_on": True,
            }
        )

    excluded_cols = {time_col}
    if inflow_col:
        excluded_cols.add(inflow_col)
    if outflow_col:
        excluded_cols.add(outflow_col)

    extra_colors = ["green", "orange", "purple", "blue", "red"]
    extra_cols = [column for column in df.columns if column not in excluded_cols]
    for idx, column in enumerate(extra_cols):
        series_specs.append(
            {
                "id": column,
                "column": column,
                "label": _column_to_label(column),
                "color": extra_colors[idx % len(extra_colors)],
                "default_on": False,
            }
        )

    series = _build_series_from_dataframe(df, time_col, series_specs)
    if not series:
        _warn("Inspect Feature", f"No plottable time-series data for structure '{struct_id}'.")
        return

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
    node_ts_multi = data.get("node_time_series_multi", {})
    merged = data.get("merged_results")

    name = str(feature["name"])

    series = _build_swmm_multi_series(node_ts_multi, name, _SWMM_NODE_METRICS)
    if (
        not series
        and node_ts is not None
        and not node_ts.empty
        and "time" in node_ts.columns
    ):
        node_col = _resolve_timeseries_column(node_ts, name)
        if node_col is not None:
            series = [
                {
                    "id": "total_inflow",
                    "x": node_ts["time"].values,
                    "y": node_ts[node_col].values,
                    "label": _SWMM_NODE_LABEL,
                    "color": "blue",
                    "default_on": True,
                }
            ]
        

    if not series:
        _warn("Inspect Feature",
              f"No time-series data for junction '{name}'.")
        return

    # Build stats from merged_results
    stats = []
    if merged is not None and not merged.empty:
        row = merged.loc[merged["node_id"] == name]
        if not row.empty:
            row = row.iloc[0]
            _add_stat_alias(
                stats,
                "Peak Inflow (cfs):",
                row,
                ("Max_Total_Inflow", "tot_inflw"),
            )
            _add_stat_alias(
                stats,
                "Time of Peak:",
                row,
                ("Time_of_Max_Inflow", "t_tot_inflw"),
                allow_text=True,
            )
            _add_stat_alias(
                stats,
                "Max HGL (ft):",
                row,
                ("Max_HGL", "max_hgl"),
            )
            _add_stat_alias(
                stats,
                "Flood Vol (MG):",
                row,
                ("Total_Flood_Volume", "flood_vol", "total_flood_volume"),
            )

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
    outfall_ts_multi = data.get("outfall_time_series_multi", {})
    outfall_loading = data.get("outfall_loading", {})

    name = str(feature["name"])

    series = _build_swmm_multi_series(outfall_ts_multi, name, _SWMM_NODE_METRICS)
    if (
        not series
        and outfall_ts is not None
        and not outfall_ts.empty
        and "time" in outfall_ts.columns
    ):
        outfall_col = _resolve_timeseries_column(outfall_ts, name)
        if outfall_col is not None:
            series = [
                {
                    "id": "flow",
                    "x": outfall_ts["time"].values,
                    "y": outfall_ts[outfall_col].values,
                    "label": _SWMM_OUTFALL_LABEL,
                    "color": "blue",
                    "default_on": True,
                }
            ]

    if not series:
        _warn("Inspect Feature",
              f"No time-series data for outfall '{name}'.")
        return

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
    link_ts_multi = data.get("link_time_series_multi", {})
    merged = data.get("merged_results")

    name = str(feature["name"])

    series = _build_swmm_multi_series(link_ts_multi, name, _SWMM_LINK_METRICS)
    if (
        not series
        and link_ts is not None
        and not link_ts.empty
        and "time" in link_ts.columns
    ):
        link_col = _resolve_timeseries_column(link_ts, name)
        if link_col is not None:
            series = [
                {
                    "id": "flow",
                    "x": link_ts["time"].values,
                    "y": link_ts[link_col].values,
                    "label": "Flow (cfs)",
                    "color": "blue",
                    "default_on": True,
                }
            ]

    if not series:
        _warn("Inspect Feature",
              f"No time-series data for conduit '{name}'.")
        return

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


def _add_stat_alias(stats_list, label, row, columns, allow_text=False):
    """Append a stat for the first available column alias."""
    for column in columns:
        if column not in row.index:
            continue

        value = row[column]
        if allow_text and not isinstance(value, (int, float)):
            stats_list.append((label, str(value) if value is not None else "N/A"))
        else:
            stats_list.append((label, _fmt(value)))
        return


def _open_dialog(title, series, stats):
    """Import and open the dialog (keeps matplotlib import lazy)."""
    from .hydrograph_dialog import HydrographDialog
    dlg = HydrographDialog(title, series, stats, parent=iface.mainWindow())
    _open_dialog_instances.append(dlg)
    dlg.destroyed.connect(
        lambda *_args, _dlg=dlg: _close_dialog_reference(_dlg)
    )
    dlg.show()


def _close_dialog_reference(dialog):
    """Remove dialog instance from strong-reference list after close."""
    try:
        _open_dialog_instances.remove(dialog)
    except ValueError:
        pass


def clear_data_cache():
    """Clear all cached extraction data."""
    _data_cache.clear()

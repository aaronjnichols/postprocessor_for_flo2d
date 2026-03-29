"""Assemble channel longitudinal and cross-section profile datasets."""

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from core.constants import GRID_ID
from core.utilities import time_function
from extraction.dat.chan_dat_extraction import extract_chan_dat
from extraction.dat.chanbank_dat_extraction import extract_chanbank_dat
from extraction.dat.xsec_dat_extraction import extract_xsec_dat
from extraction.out.chanmax_out_extraction import extract_chanmax_out
from extraction.out.chanws_out_extraction import extract_chanws_out
from extraction.out.hychan_out_extraction import extract_hychan_out


def _to_numeric(value):
    return pd.to_numeric(value, errors="coerce")


def _build_xsec_geometry(
    xsec_df: pd.DataFrame,
) -> Tuple[Dict[int, pd.DataFrame], pd.DataFrame]:
    """Return per-xsec geometry rows and summary elevations."""
    if xsec_df is None or xsec_df.empty:
        return {}, pd.DataFrame(
            columns=["xsec_number", "bed_elev", "left_bank_elev", "right_bank_elev"]
        )

    geometry_by_xsec: Dict[int, pd.DataFrame] = {}
    summary_rows = []
    grouped = xsec_df.groupby("cross_section_number", sort=False)

    for xsec_number, group in grouped:
        profile = (
            group[["station", "elevation"]]
            .copy()
            .sort_values("station")
            .reset_index(drop=True)
        )
        if profile.empty:
            continue

        geometry_by_xsec[int(xsec_number)] = profile
        left_bank_elev = float(profile.iloc[0]["elevation"])
        right_bank_elev = float(profile.iloc[-1]["elevation"])
        bed_elev = float(profile["elevation"].min())
        summary_rows.append(
            {
                "xsec_number": int(xsec_number),
                "bed_elev": bed_elev,
                "left_bank_elev": left_bank_elev,
                "right_bank_elev": right_bank_elev,
            }
        )

    return geometry_by_xsec, pd.DataFrame(summary_rows)


def _max_or_nan(series: pd.Series):
    values = _to_numeric(series)
    if values.dropna().empty:
        return float("nan")
    return float(values.max())


def _build_hychan_element_maxima(hydrographs: Dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Return per-element maxima derived from HYCHAN time series."""
    if not hydrographs:
        return pd.DataFrame(columns=["element_id"])

    rows = []
    for element_id, df in hydrographs.items():
        if df is None or df.empty:
            continue

        row = {
            "element_id": int(element_id),
            "max_elev": _max_or_nan(df.get("elev", pd.Series(dtype=float))),
            "max_discharge_hychan": _max_or_nan(
                df.get("discharge", pd.Series(dtype=float))
            ),
            "max_velocity": _max_or_nan(df.get("velocity", pd.Series(dtype=float))),
            "max_froude_no": _max_or_nan(df.get("froude_no", pd.Series(dtype=float))),
            "max_flow_area": _max_or_nan(df.get("flow_area", pd.Series(dtype=float))),
            "max_wetted_perimeter": _max_or_nan(
                df.get("wetted_perimeter", pd.Series(dtype=float))
            ),
            "max_hydraulic_radius": _max_or_nan(
                df.get("hydraulic_radius", pd.Series(dtype=float))
            ),
            "max_top_width": _max_or_nan(df.get("top_width", pd.Series(dtype=float))),
            "max_width_depth": _max_or_nan(
                df.get("width_depth", pd.Series(dtype=float))
            ),
            "max_energy_slope": _max_or_nan(
                df.get("energy_slope", pd.Series(dtype=float))
            ),
            "max_bed_shear_stress": _max_or_nan(
                df.get("bed_shear_stress", pd.Series(dtype=float))
            ),
            "max_surface_area": _max_or_nan(
                df.get("surface_area", pd.Series(dtype=float))
            ),
            "time_peak_q_hychan": float("nan"),
        }

        if "discharge" in df.columns and "time" in df.columns:
            q = _to_numeric(df["discharge"])
            t = _to_numeric(df["time"])
            valid = q.notna() & t.notna()
            if valid.any():
                peak_idx = q[valid].idxmax()
                row["time_peak_q_hychan"] = float(t.loc[peak_idx])

        rows.append(row)

    return pd.DataFrame(rows)


def _compute_chainage(group: pd.DataFrame) -> pd.Series:
    lengths = _to_numeric(group.get("length_ft", pd.Series(dtype=float))).fillna(0.0)
    if lengths.empty:
        return pd.Series(dtype=float)

    if float(lengths.sum()) <= 0.0:
        return pd.Series(range(len(group)), index=group.index, dtype=float)

    start = lengths.cumsum().shift(fill_value=0.0)
    return start + (lengths / 2.0)


def _coalesce_max_water(row):
    for column in ("max_wse", "max_stage", "max_elev"):
        value = row.get(column)
        if pd.notna(value):
            return float(value)
    return float("nan")


@time_function
def extract_channel_profile_dataset(folder_path: str) -> dict:
    """Build channel segment profile and cross-section lookup datasets."""
    chan_data = extract_chan_dat(folder_path)
    channels = chan_data.get("channels", pd.DataFrame()).copy()
    chanbank_df = extract_chanbank_dat(folder_path)

    try:
        xsec_df = extract_xsec_dat(folder_path)
    except FileNotFoundError:
        xsec_df = pd.DataFrame(columns=["cross_section_number", "station", "elevation"])

    try:
        chanmax_df = extract_chanmax_out(folder_path)
    except FileNotFoundError:
        chanmax_df = pd.DataFrame(
            columns=["id", "max_discharge", "time_max_discharge", "max_stage", "time_max_stage"]
        )

    try:
        chanws_df = extract_chanws_out(folder_path)
    except FileNotFoundError:
        chanws_df = pd.DataFrame(columns=["element_id", "x", "y", "max_wse"])

    try:
        hychan_by_element = extract_hychan_out(folder_path)
    except FileNotFoundError:
        hychan_by_element = {}

    xsec_geometry, xsec_summary = _build_xsec_geometry(xsec_df)
    hychan_maxima = _build_hychan_element_maxima(hychan_by_element)

    if channels.empty:
        return {
            "segment_profiles": {},
            "xsec_lookup": pd.DataFrame(),
            "xsec_geometry": xsec_geometry,
            "element_hydrographs": hychan_by_element,
            "element_maxima": hychan_maxima,
        }

    channels = channels.reset_index(drop=True)
    channels["xsec_id"] = channels.index + 1
    channels["segment_id"] = _to_numeric(channels["segment_id"]).fillna(0).astype(int) + 1
    channels["element_id"] = _to_numeric(channels[GRID_ID]).fillna(-1).astype(int) + 1
    channels["xsec_number"] = _to_numeric(channels.get("xsec_number"))
    channels["length_ft"] = _to_numeric(channels.get("length"))

    if chanbank_df is not None and not chanbank_df.empty:
        chanbank = chanbank_df.copy()
        chanbank["xsec_id"] = _to_numeric(chanbank["xsec_id"]).astype("Int64")
        chanbank["left_bank"] = _to_numeric(chanbank["left_bank"]).astype("Int64")
        chanbank["right_bank"] = _to_numeric(chanbank["right_bank"]).astype("Int64")
        channels = channels.merge(chanbank, on="xsec_id", how="left")
        # Layer features and HYCHAN use raw FLO-2D element ids; prefer left bank id.
        channels["element_id"] = _to_numeric(channels["left_bank"]).fillna(
            _to_numeric(channels["element_id"])
        )
    else:
        channels["left_bank"] = pd.NA
        channels["right_bank"] = pd.NA

    channels["element_id"] = _to_numeric(channels["element_id"]).astype("Int64")

    if not chanmax_df.empty and GRID_ID in chanmax_df.columns:
        chanmax = chanmax_df.copy()
        chanmax["element_id"] = _to_numeric(chanmax[GRID_ID]).astype("Int64") + 1
        chanmax = chanmax[
            ["element_id", "max_discharge", "time_max_discharge", "max_stage", "time_max_stage"]
        ]
        channels = channels.merge(chanmax, on="element_id", how="left")

    if chanws_df is not None and not chanws_df.empty:
        chanws = chanws_df.copy()
        chanws["element_id"] = _to_numeric(chanws["element_id"]).astype("Int64")
        channels = channels.merge(chanws[["element_id", "max_wse"]], on="element_id", how="left")

    if not hychan_maxima.empty:
        hychan_maxima["element_id"] = _to_numeric(hychan_maxima["element_id"]).astype("Int64")
        channels = channels.merge(hychan_maxima, on="element_id", how="left")

    if not xsec_summary.empty:
        xsec_summary = xsec_summary.copy()
        xsec_summary["xsec_number"] = _to_numeric(xsec_summary["xsec_number"]).astype("Int64")
        channels["xsec_number"] = _to_numeric(channels["xsec_number"]).astype("Int64")
        channels = channels.merge(xsec_summary, on="xsec_number", how="left")

    channels["max_water_surface"] = channels.apply(_coalesce_max_water, axis=1)

    channels["chainage_ft"] = 0.0
    for segment_id, group in channels.groupby("segment_id", sort=False):
        ordered = group.sort_values("xsec_id")
        chainage = _compute_chainage(ordered)
        channels.loc[ordered.index, "chainage_ft"] = chainage.values

    channels = channels.sort_values(["segment_id", "xsec_id"]).reset_index(drop=True)

    segment_profiles = {}
    for segment_id, group in channels.groupby("segment_id", sort=False):
        segment_profiles[int(segment_id)] = (
            group.sort_values("chainage_ft").reset_index(drop=True)
        )

    xsec_lookup_columns = [
        "segment_id",
        "xsec_id",
        "element_id",
        "xsec_number",
        "length_ft",
        "chainage_ft",
        "left_bank",
        "right_bank",
        "max_discharge",
        "time_max_discharge",
        "max_stage",
        "time_max_stage",
        "max_wse",
        "max_water_surface",
        "max_elev",
    ]
    xsec_lookup = channels[xsec_lookup_columns].copy()

    return {
        "segment_profiles": segment_profiles,
        "xsec_lookup": xsec_lookup,
        "xsec_geometry": xsec_geometry,
        "element_hydrographs": hychan_by_element,
        "element_maxima": hychan_maxima,
    }

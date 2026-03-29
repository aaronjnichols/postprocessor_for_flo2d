"""Unit tests for assembled channel profile datasets."""

from __future__ import annotations

from extraction.out.channel_profile_out_extraction import extract_channel_profile_dataset


def _write_minimal_channel_files(base):
    (base / "CHAN.DAT").write_text(
        "\n".join(
            [
                "0.00 0.00 0.30",
                "N 1001 0.02 25.0 1",
                "N 1002 0.02 30.0 2",
            ]
        ),
        encoding="utf-8",
    )
    (base / "CHANBANK.DAT").write_text("1001 2001\n1002 2002\n", encoding="utf-8")
    (base / "XSEC.DAT").write_text(
        "\n".join(
            [
                "X 1 XS-1",
                "0.0 11.5",
                "10.0 10.0",
                "20.0 11.7",
                "X 2 XS-2",
                "0.0 12.5",
                "10.0 11.0",
                "20.0 12.7",
            ]
        ),
        encoding="utf-8",
    )
    (base / "CHANMAX.OUT").write_text(
        "\n".join(
            [
                "1001 20.0 1.25 11.0 1.25",
                "1002 25.0 1.50 12.0 1.50",
            ]
        ),
        encoding="utf-8",
    )
    (base / "CHANWS.OUT").write_text(
        "\n".join(
            [
                "1001 0.0 0.0 11.2",
                "1002 0.0 0.0 12.4",
            ]
        ),
        encoding="utf-8",
    )
    (base / "HYCHAN.OUT").write_text(
        """
     CHANNEL HYDROGRAPH FOR ELEMENT NO:  1001
       0.00      10.00         1.00         2.00         3.00      0.10         4.00              5.00             0.80          6.00         7.00       0.010000          0.20000          8.00
       0.25      11.00         1.10         2.10         4.00      0.11         4.10              5.10             0.81          6.10         7.10       0.011000          0.21000          8.10

     CHANNEL HYDROGRAPH FOR ELEMENT NO:  1002
       0.00      11.00         1.20         2.20         5.00      0.12         4.20              5.20             0.82          6.20         7.20       0.012000          0.22000          8.20
       0.25      12.00         1.30         2.30         6.00      0.13         4.30              5.30             0.83          6.30         7.30       0.013000          0.23000          8.30
""",
        encoding="utf-8",
    )


def test_extract_channel_profile_dataset_builds_segment_profiles(tmp_path):
    _write_minimal_channel_files(tmp_path)

    dataset = extract_channel_profile_dataset(str(tmp_path))
    assert sorted(dataset["segment_profiles"]) == [1]

    seg_df = dataset["segment_profiles"][1]
    assert list(seg_df["xsec_id"]) == [1, 2]
    assert list(seg_df["element_id"]) == [1001, 1002]
    assert round(float(seg_df["chainage_ft"].iloc[0]), 2) == 12.50
    assert round(float(seg_df["chainage_ft"].iloc[1]), 2) == 40.00
    assert round(float(seg_df["max_water_surface"].iloc[0]), 2) == 11.20
    assert round(float(seg_df["max_water_surface"].iloc[1]), 2) == 12.40

    xsec_lookup = dataset["xsec_lookup"]
    assert set(
        [
            "segment_id",
            "xsec_id",
            "element_id",
            "xsec_number",
            "max_stage",
            "max_wse",
            "max_water_surface",
        ]
    ).issubset(
        xsec_lookup.columns
    )
    row1 = xsec_lookup.loc[xsec_lookup["xsec_id"] == 1].iloc[0]
    assert round(float(row1["max_stage"]), 2) == 11.00
    assert round(float(row1["max_water_surface"]), 2) == 11.20

    xsec_geometry = dataset["xsec_geometry"]
    assert sorted(xsec_geometry) == [1, 2]
    assert list(xsec_geometry[1].columns) == ["station", "elevation"]

    hydrographs = dataset["element_hydrographs"]
    assert sorted(hydrographs) == [1001, 1002]

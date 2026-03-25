"""Unit tests for the supported FLO-2D file registry."""

from __future__ import annotations

from core.supported_files import (
    describe_project_marker_examples,
    folder_contains_supported_files,
    get_file_extractors,
    get_legacy_file_aliases,
    get_model_extractor_registry,
    get_required_model_files,
    get_supported_files_by_category,
    list_present_validation_marker_files,
)


def test_supported_files_registry_tracks_hydrostruct_and_levee():
    categories = get_supported_files_by_category()

    assert "HYDROSTRUCT.OUT" in categories["output_files"]
    assert "LEVEE.DAT" in categories["optional_inputs"]


def test_file_extractors_include_centralized_supported_files():
    extractors = get_file_extractors()

    assert "HYDROSTRUCT.OUT" in extractors
    assert "LEVEE.DAT" in extractors


def test_model_extractor_registry_exposes_required_depth_out():
    registry = get_model_extractor_registry()

    assert "DEPTH.OUT" in registry
    assert get_required_model_files() == ("DEPTH.OUT",)


def test_folder_markers_detect_supported_projects(tmp_path):
    (tmp_path / "HYDROSTRUCT.OUT").write_text("S 1\n", encoding="utf-8")

    assert folder_contains_supported_files(str(tmp_path))
    assert list_present_validation_marker_files(str(tmp_path)) == ["HYDROSTRUCT.OUT"]


def test_legacy_aliases_and_marker_examples_stay_available():
    aliases = get_legacy_file_aliases()
    examples = describe_project_marker_examples()

    assert aliases["OUTNQ"] == "OUTNQ.OUT"
    assert "CADPTS.DAT" in examples

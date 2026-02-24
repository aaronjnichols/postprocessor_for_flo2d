"""Tests for QGIS plugin project-root discovery helpers."""

from __future__ import annotations

import os
import sys

from qgis_plugin.project_root import discover_project_root, ensure_project_root_on_path


def _make_fake_repo(root):
    os.makedirs(os.path.join(root, "core"), exist_ok=True)
    os.makedirs(os.path.join(root, "extraction"), exist_ok=True)
    os.makedirs(os.path.join(root, "processing"), exist_ok=True)
    with open(os.path.join(root, "main.py"), "w", encoding="utf-8") as handle:
        handle.write("# test")


def test_discover_project_root_uses_hint_file(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugins" / "flo2d_postprocessor"
    plugin_dir.mkdir(parents=True)

    repo_root = tmp_path / "repo_root"
    _make_fake_repo(str(repo_root))

    hint = plugin_dir / "project_root.txt"
    hint.write_text(str(repo_root), encoding="utf-8")

    monkeypatch.setenv("PYTHONPATH", "")
    plugin_file = str(plugin_dir / "hydrograph_action.py")

    discovered = discover_project_root(plugin_file)
    assert os.path.normcase(discovered) == os.path.normcase(str(repo_root))


def test_ensure_project_root_on_path_inserts_once(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugins" / "flo2d_postprocessor"
    plugin_dir.mkdir(parents=True)

    repo_root = tmp_path / "repo_root"
    _make_fake_repo(str(repo_root))

    hint = plugin_dir / "project_root.txt"
    hint.write_text(str(repo_root), encoding="utf-8")

    monkeypatch.setenv("PYTHONPATH", "")
    plugin_file = str(plugin_dir / "processing_worker.py")

    original = list(sys.path)
    try:
        root_1, inserted_1 = ensure_project_root_on_path(plugin_file)
        root_2, inserted_2 = ensure_project_root_on_path(plugin_file)
    finally:
        sys.path[:] = original

    assert os.path.normcase(root_1) == os.path.normcase(str(repo_root))
    assert os.path.normcase(root_2) == os.path.normcase(str(repo_root))
    assert inserted_1 is True
    assert inserted_2 is False

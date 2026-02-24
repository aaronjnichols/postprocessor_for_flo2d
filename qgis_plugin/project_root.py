"""Helpers for locating the FLO-2D postprocessor project root."""

from __future__ import annotations

import os
import sys
from typing import Iterable, Optional, Tuple


def _is_project_root(path: str) -> bool:
    """Return True when *path* looks like the postprocessor repository root."""
    if not path:
        return False
    return (
        os.path.isdir(os.path.join(path, "core"))
        and os.path.isdir(os.path.join(path, "extraction"))
        and os.path.isdir(os.path.join(path, "processing"))
        and os.path.isfile(os.path.join(path, "main.py"))
    )


def _load_root_hint(plugin_dir: str) -> Optional[str]:
    """Read a project-root hint file from the installed plugin directory."""
    hint_path = os.path.join(plugin_dir, "project_root.txt")
    if not os.path.isfile(hint_path):
        return None
    try:
        with open(hint_path, "r", encoding="utf-8") as handle:
            value = handle.readline().strip()
    except OSError:
        return None
    return value or None


def _iter_candidate_roots(plugin_dir: str) -> Iterable[str]:
    """Yield candidate root directories in priority order."""
    # Legacy expectation: plugin was copied under repo root.
    yield os.path.dirname(plugin_dir)

    # Preferred explicit hint written by install script.
    hint = _load_root_hint(plugin_dir)
    if hint:
        yield hint

    # Optional dedicated environment variable.
    env_root = os.environ.get("FLO2D_POSTPROCESSOR_ROOT")
    if env_root:
        yield env_root

    # Generic PYTHONPATH entries.
    pythonpath = os.environ.get("PYTHONPATH", "")
    for item in pythonpath.split(os.pathsep):
        item = item.strip()
        if item:
            yield item

    # Final fallback: current working directory.
    yield os.getcwd()


def discover_project_root(plugin_file: str) -> Optional[str]:
    """Find the repository root that contains extraction/core packages."""
    plugin_dir = os.path.dirname(os.path.abspath(plugin_file))
    seen = set()
    for candidate in _iter_candidate_roots(plugin_dir):
        normalized = os.path.normcase(os.path.normpath(os.path.abspath(candidate)))
        if normalized in seen:
            continue
        seen.add(normalized)
        if _is_project_root(candidate):
            return os.path.abspath(candidate)
    return None


def ensure_project_root_on_path(plugin_file: str) -> Tuple[Optional[str], bool]:
    """Ensure a discovered project root is on sys.path.

    Returns:
        tuple: (project_root_or_none, inserted_bool)
    """
    project_root = discover_project_root(plugin_file)
    if not project_root:
        return None, False
    if project_root in sys.path:
        return project_root, False
    sys.path.insert(0, project_root)
    return project_root, True

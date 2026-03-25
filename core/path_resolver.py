"""Helpers for resolving FLO-2D inputs passed as folders or explicit files."""

from __future__ import annotations

import os
from typing import Union


PathLike = Union[str, os.PathLike]


def resolve_model_file_path(path: PathLike, filename: str) -> str:
    """Return the path to ``filename`` for either a project folder or file input."""
    candidate = os.path.normpath(os.fspath(path))
    basename = os.path.basename(candidate)

    if os.path.isdir(candidate):
        return os.path.join(candidate, filename)

    if basename.lower() == filename.lower():
        return candidate

    if os.path.exists(candidate) and os.path.isfile(candidate):
        raise ValueError(f"Expected {filename}, but received explicit path to {basename}")

    _, extension = os.path.splitext(basename)
    if extension:
        return candidate

    return os.path.join(candidate, filename)

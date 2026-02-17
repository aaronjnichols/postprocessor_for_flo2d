"""Helpers for discovering postprocessor output folders."""

import os


def get_vector_output_dirs(project_folder):
    """Return existing vector output dirs, supporting legacy naming."""
    candidate_dirs = [
        os.path.join(project_folder, "flo2d_shp"),
        os.path.join(project_folder, "FLO2D_SHP"),
    ]

    existing_dirs = []
    seen = set()
    for candidate in candidate_dirs:
        normalized = os.path.normcase(os.path.normpath(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)
        if os.path.isdir(candidate):
            existing_dirs.append(candidate)

    return existing_dirs

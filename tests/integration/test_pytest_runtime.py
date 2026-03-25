"""Integration coverage for the repo-local pytest runtime configuration."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTEST_TARGET = (
    "tests/integration/test_file_discovery.py::"
    "TestFileDiscoveryIntegration::test_file_discovery_missing_files"
)
PYTEST_EXE = REPO_ROOT / ".venv" / "Scripts" / "pytest.exe"


def _pytest_commands():
    commands = [
        pytest.param(
            [sys.executable, "-m", "pytest"],
            id="python-m-pytest",
        )
    ]

    if PYTEST_EXE.exists():
        commands.append(
            pytest.param(
                [str(PYTEST_EXE)],
                id="pytest-exe",
            )
        )

    return commands


@pytest.mark.parametrize("command", _pytest_commands())
def test_pytest_uses_repo_local_runtime_without_warning(command: list[str]) -> None:
    result = subprocess.run(
        [*command, PYTEST_TARGET, "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_output = "\n".join(
        output for output in (result.stdout, result.stderr) if output
    )

    assert result.returncode == 0, combined_output
    assert "PytestCacheWarning" not in combined_output
    assert "PermissionError" not in combined_output
    assert (REPO_ROOT / "pytest_runtime" / ".pytest_cache").is_dir()

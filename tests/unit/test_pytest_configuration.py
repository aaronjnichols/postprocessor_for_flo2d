"""Regression coverage for pytest project configuration."""

from configparser import ConfigParser
from pathlib import Path

import pytest

import sitecustomize


REPO_ROOT = Path(__file__).resolve().parents[2]


def _get_multiline_values(parser: ConfigParser, section: str, option: str) -> set[str]:
    value = parser.get(section, option)
    return {line.strip() for line in value.splitlines() if line.strip()}


def test_pytest_ini_uses_supported_section_and_local_workdirs() -> None:
    parser = ConfigParser()
    parser.read(REPO_ROOT / "pytest.ini")

    assert parser.has_section("pytest")
    assert not parser.has_section("tool:pytest")
    assert parser.get("pytest", "cache_dir") == "pytest_runtime/.pytest_cache"

    addopts = parser.get("pytest", "addopts")
    assert "--basetemp" not in addopts
    assert "--cov-exclude" not in addopts


def test_pytest_ini_registers_project_markers() -> None:
    parser = ConfigParser()
    parser.read(REPO_ROOT / "pytest.ini")

    markers = _get_multiline_values(parser, "pytest", "markers")

    assert {
        "unit: Unit tests",
        "integration: Integration tests",
        "slow: Slow running tests",
        "data_validation: Data validation tests",
    } <= markers


def test_coveragerc_omits_non_source_paths() -> None:
    parser = ConfigParser()
    parser.read(REPO_ROOT / ".coveragerc")

    assert parser.has_section("run")
    assert parser.get("run", "data_file") == "pytest_runtime/.coverage"
    assert {"tests/*", "gui/*", "setup.py"} <= _get_multiline_values(
        parser, "run", "omit"
    )


@pytest.mark.parametrize(
    ("orig_argv", "argv", "expected"),
    [
        (["python", "-m", "pytest"], ["pytest"], True),
        (
            [r"C:\_code\postprocessor_for_flo2d\.venv\Scripts\pytest.exe"],
            [r"C:\_code\postprocessor_for_flo2d\.venv\Scripts\pytest.exe"],
            True,
        ),
        (
            [r"C:\_code\postprocessor_for_flo2d\.venv\Scripts\py.test.exe"],
            [r"C:\_code\postprocessor_for_flo2d\.venv\Scripts\py.test.exe"],
            True,
        ),
        (["python", "main.py"], ["main.py"], False),
    ],
)
def test_sitecustomize_detects_pytest_launchers(
    monkeypatch: pytest.MonkeyPatch,
    orig_argv: list[str],
    argv: list[str],
    expected: bool,
) -> None:
    monkeypatch.setattr(sitecustomize.sys, "orig_argv", orig_argv, raising=False)
    monkeypatch.setattr(sitecustomize.sys, "argv", argv)

    assert sitecustomize._running_pytest() is expected

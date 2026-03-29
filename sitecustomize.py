"""Early runtime tweaks for local pytest execution in sandboxed Windows environments."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Callable, TypeVar


REPO_ROOT = Path(__file__).resolve().parent
PYTEST_WORKDIR = REPO_ROOT / "pytest_runtime"
PatchFunc = TypeVar("PatchFunc", bound=Callable[..., object])
_ORIGINAL_PATH_MKDIR = Path.mkdir
_ORIGINAL_PATH_CHMOD = Path.chmod
_ORIGINAL_RMTREE = shutil.rmtree


def _ignore_permission_error(func: PatchFunc) -> PatchFunc:
    def wrapped(*args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return func(*args, **kwargs)
        except PermissionError:
            return None

    return wrapped  # type: ignore[return-value]


def _is_pytest_runtime_path(path: Path) -> bool:
    candidate_text = str(path)
    if candidate_text.startswith("\\\\?\\"):
        candidate_text = candidate_text[4:]

    runtime_text = str(PYTEST_WORKDIR.resolve(strict=False))
    if runtime_text.startswith("\\\\?\\"):
        runtime_text = runtime_text[4:]

    candidate = Path(os.path.abspath(candidate_text))
    runtime_root = Path(os.path.abspath(runtime_text))
    return os.path.normcase(str(candidate)).startswith(os.path.normcase(str(runtime_root)))


def _mkdir_with_default_permissions(
    self: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
) -> None:
    if _is_pytest_runtime_path(self):
        _ORIGINAL_PATH_MKDIR(self, parents=parents, exist_ok=exist_ok)
        return None

    _ORIGINAL_PATH_MKDIR(self, mode=mode, parents=parents, exist_ok=exist_ok)
    return None


def _chmod_with_permission_fallback(
    self: Path, mode: int, *, follow_symlinks: bool = True
) -> None:
    try:
        _ORIGINAL_PATH_CHMOD(self, mode, follow_symlinks=follow_symlinks)
    except PermissionError:
        if _is_pytest_runtime_path(self):
            return None
        raise

    return None


def _rmtree_with_permission_fallback(path, *args, **kwargs):  # type: ignore[no-untyped-def]
    try:
        return _ORIGINAL_RMTREE(path, *args, **kwargs)
    except PermissionError:
        if _is_pytest_runtime_path(Path(path)):
            fallback_kwargs = dict(kwargs)
            fallback_kwargs["ignore_errors"] = True
            return _ORIGINAL_RMTREE(path, *args, **fallback_kwargs)
        raise


def _write_text_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="UTF-8")


def _write_bytes_if_missing(path: Path, content: bytes) -> None:
    if not path.exists():
        path.write_bytes(content)


def _running_pytest() -> bool:
    argv = [argument.lower() for argument in getattr(sys, "orig_argv", [])]
    argv.extend(argument.lower() for argument in sys.argv)
    for argument in argv:
        command_name = Path(argument).name
        for suffix in (".exe", "-script.py", "-script.pyw"):
            if command_name.endswith(suffix):
                command_name = command_name[: -len(suffix)]
                break

        if command_name in {"pytest", "py.test"}:
            return True

    return False


if _running_pytest():
    os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(PYTEST_WORKDIR))
    os.environ.setdefault("COVERAGE_FILE", str(PYTEST_WORKDIR / ".coverage"))
    Path.mkdir = _mkdir_with_default_permissions
    Path.chmod = _chmod_with_permission_fallback
    shutil.rmtree = _rmtree_with_permission_fallback

    import _pytest.pathlib as pytest_pathlib
    import _pytest.tmpdir as pytest_tmpdir
    import _pytest.cacheprovider as pytest_cacheprovider
    import coverage.data as coverage_data
    import coverage.misc as coverage_misc
    import coverage.sqldata as coverage_sqldata

    original_ensure_cache_dir = (
        pytest_cacheprovider.Cache._ensure_cache_dir_and_supporting_files
    )

    def _ensure_cache_dir_with_runtime_fallback(self) -> None:  # type: ignore[no-untyped-def]
        if not _is_pytest_runtime_path(self._cachedir):
            original_ensure_cache_dir(self)
            return None

        if self._cachedir.is_dir():
            return None

        self._cachedir.parent.mkdir(parents=True, exist_ok=True)
        self._cachedir.mkdir(parents=True, exist_ok=True)
        _write_text_if_missing(
            self._cachedir / "README.md", pytest_cacheprovider.README_CONTENT
        )
        _write_text_if_missing(
            self._cachedir / ".gitignore", "# Created by pytest automatically.\n*\n"
        )
        _write_bytes_if_missing(
            self._cachedir / "CACHEDIR.TAG",
            pytest_cacheprovider.CACHEDIR_TAG_CONTENT,
        )
        return None

    pytest_cacheprovider.Cache._ensure_cache_dir_and_supporting_files = (
        _ensure_cache_dir_with_runtime_fallback
    )
    pytest_pathlib.cleanup_dead_symlinks = _ignore_permission_error(
        pytest_pathlib.cleanup_dead_symlinks
    )
    pytest_tmpdir.cleanup_dead_symlinks = _ignore_permission_error(
        pytest_tmpdir.cleanup_dead_symlinks
    )
    coverage_data.file_be_gone = _ignore_permission_error(coverage_data.file_be_gone)
    coverage_misc.file_be_gone = _ignore_permission_error(coverage_misc.file_be_gone)
    coverage_sqldata.file_be_gone = _ignore_permission_error(
        coverage_sqldata.file_be_gone
    )

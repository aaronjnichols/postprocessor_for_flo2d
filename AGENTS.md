# Repository Guidelines

## Project Structure & Module Organization
- `core/`: shared utilities, logging, file discovery, model data extraction.
- `extraction/`: readers for FLO-2D `*.DAT` and `*.OUT` (subfolders `dat/`, `out/`, `base/`). Keep new extractors consistent: `<topic>_dat_extraction.py` or `<topic>_out_extraction.py`.
- `processing/`: spatial/vectorization and geospatial helpers.
- `reporting/`: spreadsheet and visualization outputs.
- `gui/`: Tk-based launcher and messaging integration.
- `tests/`: `unit/`, `integration/`, and `fixtures/` (synthetic models and error cases).
- `tools/`: packaging/build scripts (`build_exe.py`, `build_installer.bat`).
- `scripts/`: local setup and convenience launchers (e.g., `run_gui.bat`).
- `docs/`: style guide, user manual, deployment notes.

## Build, Test, and Development Commands
- Environment: `python -m venv .venv && .\.venv\Scripts\activate`
- Install deps: `pip install -r requirements.txt` (+ tests: `pip install -r test-requirements.txt`)
- Quick setup (Windows): `scripts\setup.bat`
- Run CLI: `python main.py -h` (see `config.example.json` for inputs)
- Run GUI: `scripts\run_gui.bat` or `python gui\launch_gui.py`
- Tests: `pytest` (unit only: `pytest tests\unit -q`; single file: `pytest tests\unit\test_chan_extraction.py -q`)
- Build executable/installer: `python tools\build_exe.py`, then `tools\build_installer.bat`

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indents; prefer type hints for new/edited code.
- Filenames and functions: `snake_case`; classes: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
- Keep extractor/module naming consistent with existing patterns in `extraction/`.
- Logging goes through `core/logger.py`; avoid ad-hoc print statements.
- See `docs/STYLE_GUIDE.md` for additional rules and examples.

## Testing Guidelines
- Framework: `pytest` with tests under `tests/unit` and `tests/integration`.
- Name tests `test_*.py`; add reusable data under `tests/fixtures`.
- Aim to cover new branches/edge cases; prefer deterministic synthetic inputs.
- Run `pytest -q` locally before pushing; add regression tests for bug fixes.

## Commit & Pull Request Guidelines
- Style follows Conventional Commits seen in history: `feat: …`, `fix: …`, `docs: …`, `refactor: …`.
- Commit messages: imperative mood, concise subject; include scope when helpful.
- PRs: clear description, linked issues, reproduction steps, and screenshots/GIFs for GUI changes. Note impacts to outputs/filenames.
- Update `CHANGELOG.md` when adding user-visible features or fixes.

## Security & Configuration Tips
- Copy `config.example.json` to `config.json` for local settings; do not commit secrets or proprietary datasets.
- Large files and generated outputs should not live in the repo; use paths via config.

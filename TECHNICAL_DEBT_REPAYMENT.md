# Technical Debt Repayment Plan

This document lays out a pragmatic, phased plan to understand, stabilize, and improve this codebase. The focus is maintainability, correctness, performance, and developer ergonomics while respecting the existing project structure and guidelines.

Goals
- Build a working mental model of the system and data flows.
- Reduce future change risk via tests, types, and clearer module boundaries.
- Remove dead code and align naming/structure with repo conventions.
- Standardize logging, configs, and error handling.
- Establish CI that catches regressions on Windows (primary target) and other platforms.

Guiding Principles
- Prefer small, incremental PRs; one logical change per PR.
- Follow docs/STYLE_GUIDE.md, PEP 8, and naming conventions (snake_case for files/functions, PascalCase for classes).
- Use core/logger.py for logging; avoid print statements.
- Update docs and tests with any user-visible change.
- Use Conventional Commits (feat:, fix:, refactor:, chore:, docs:, test:, perf:, ci:).

Quick Wins (Week 0)
- Remove obvious artifacts and duplicates (e.g., debug scripts already removed).
- Standardize file/module names for SWMM extractors (e.g., swmm_links_rpt.py vs swmmlinks_rpt.py).
- Replace stray print calls with logger.
- Add smoke tests for CLI and GUI launch.

Phase 1 — Baseline & Inventory (Day 1–3)
- Environment: create venv; install requirements and test-requirements.
- Run: `pytest -q` to establish baseline; note failures/flakes.
- Scan for common smells:
  - `rg -n "print\("` (replace with logger)
  - `rg -n "TODO|FIXME|HACK|XXX"`
  - `rg -n "except Exception"` (tighten exception scopes)
  - `rg -n "import .* as .*"` or unused imports
  - `rg -n "sys\.path\.append"` (prefer relative imports within package)
  - `rg -n "swmmlinks_rpt|swmm_links_rpt"` (naming drift)
  - `rg --files | sort` to visually review layout vs. Repository Guidelines.
- Document findings in a running WORKLOG (see template at end) and create a checklist of small PRs.

Deliverables
- A short ARCHITECTURE.md (high-level data flow, major modules, key data artifacts).
- A module responsibility map: core/, extraction/, processing/, reporting/, gui/.
- A list of quick refactors (<= 2 hours each) with an owner and priority.

Phase 2 — Logging & Error Handling (Day 3–5)
- Replace `print` with project logger (core/logger.py) across modules.
- Ensure top-level entry points (CLI/GUI) configure logging once.
- Introduce a simple exception taxonomy (e.g., ExtractionError, ProcessingError, ReportingError) and raise them at module boundaries.
- Ensure errors propagate to CLI exit codes and GUI messaging consistently.

Checklist
- Consistent log formats; no duplicate handlers.
- Catch-and-log at boundaries; no silent failures.
- Remove `logging.basicConfig` calls inside libraries.

Phase 3 — Configuration Hygiene (Day 5–7)
- Ensure `config.example.json` contains all required keys with comments.
- Add a small config validation step at startup (type/required checks with helpful messages).
- Allow env var overrides (optional), but do not commit secrets.
- Verify large file/output paths are configured via config, not hard-coded.

Phase 4 — Extraction Layer Consistency (Week 2)
- Naming: keep extractors in `extraction/dat` (for *.DAT/INP) and `extraction/out` (for *.OUT/*.RPT) using `<topic>_dat_extraction.py` or `<topic>_out_extraction.py`.
- Standardize function signatures and returns:
  - Input: `pathlib.Path | str` for file paths, plus optional CRS/units.
  - Output: structured types with type hints (DataFrame, dict[str, DataFrame], or dataclasses for well-known schemas).
- Add clear docstrings: expected input files, parsing assumptions, returned columns and units.
- Robust parsing: handle encoding, partial/malformed rows, and informative errors.
- Unify SWMM RPT extractor column naming (`node_id`, `link_id`, metrics like `max_depth_ft`, `peak_flow_cfs`, etc.).

Tests
- Unit tests for each extractor using synthetic fixtures under `tests/fixtures`.
- Golden files for a few small, deterministic inputs (assert row counts and key columns).

Phase 5 — Processing & Vectorization (Week 3)
- Confirm CRS handling is explicit and consistent (store EPSG in outputs; avoid implicit assumptions).
- Validate geometries (fix invalids, drop empties); log counts pre/post.
- Streaming/chunked workflows for large datasets where feasible.
- Ensure `create_swmm_shapefiles` accepts optional merged RPT DataFrames with well-defined join keys.
- Add basic performance profiling on hot paths (vectorization, rasterization, spreadsheet generation).

Phase 6 — Reporting (Week 3–4)
- Define consistent column names and units in spreadsheets; centralize format helpers.
- Ensure charts/plots are deterministic; remove non-deterministic randomness.
- Cap workbook size; split large sheets or provide CSV fallbacks when row counts exceed thresholds.
- Validate that spreadsheet generation gracefully handles missing or partial inputs.

Phase 7 — CLI & GUI Coherence (Week 4)
- CLI: `python main.py -h` shows clear subcommands/flags; errors exit non-zero.
- GUI: align options with CLI; use consistent progress/messaging.
- Avoid duplicating business logic: route through shared helpers.

Phase 8 — Tests & Coverage (Week 4–5)
- Unit tests for core utilities, extractors, processors, reporters.
- Integration tests using minimal synthetic models (tests/integration) covering end-to-end happy paths for: FLO-2D only, SWMM only, combined flows.
- Add property-based tests for parsing edge cases (optional, via `hypothesis`).
- Target: cover main branches and error paths most likely to break.

Phase 9 — Dependencies & Tooling (Week 5)
- Requirements: pin versions where stability matters; add markers for optional features.
- Remove unused dependencies; add `pip check` to CI.
- Lint/format: adopt `ruff` (lint) and `black` (format) if not already configured; run in CI.
- Type checking: add `mypy` with gradual typing; enable in CI but start permissive.

Phase 10 — CI/CD (Week 5–6)
- GitHub Actions pipeline (Windows + Ubuntu):
  - Setup Python, cache pip, install reqs
  - Lint, type-check, run tests
  - Build executable via `tools/build_exe.py` (Windows job)
- Release process: tag → build → attach artifacts; update CHANGELOG.md.

Phase 11 — Documentation (continuous)
- docs/ARCHITECTURE.md: diagrams of data flow: extraction → processing → reporting → outputs.
- docs/DEVELOPER_GUIDE.md: how to run, debug, test, add new extractor.
- docs/CONTRIBUTING.md: coding style, commit messages, PR expectations.
- Keep user-facing docs focused on setup and usage; add screenshots for GUI.

Refactoring Opportunities (Initial Backlog)
- Normalize SWMM RPT extractor naming (swmm_links_rpt.py vs swmmlinks_rpt.py); ensure only one is referenced.
- Centralize column name constants for SWMM nodes/links/outfalls; avoid string duplication.
- Consolidate repeated shapefile writing logic into a single helper with strategy hooks (points/lines/polygons).
- Replace ad-hoc path handling with pathlib throughout.
- Eliminate `sys.path.append` usage; rely on package-relative imports.
- Introduce small data-layer helpers for schema validation of DataFrames (presence/type of key columns).

Data Contracts (Schemas)
- Define explicit schemas for key data structures (e.g., SWMM junctions summary, links summary):
  - Required columns, types, units (document in code docstrings and docs/SCHEMAS.md).
  - Validate at boundaries; fail with actionable messages.

Performance Notes
- Use `pyogrio` or `fiona` with layer options for faster I/O where available.
- Consider GeoPackage as default when file count explodes; provide toggles in config.
- Batch or parallelize CPU-heavy phases with ThreadPoolExecutor/ProcessPoolExecutor where safe.

Security & Safety
- No secrets or proprietary datasets in the repo.
- Avoid executing user-provided code; validate inputs and sanitize file paths.
- Handle large files gracefully; document memory expectations.

Acceptance Criteria
- Tests pass reliably on CI (Windows and Ubuntu).
- Logging is consistent and helpful.
- No stray debug code or prints.
- Extractors and processors have docstrings, types, and deterministic tests.
- Naming and file locations align with Repository Guidelines.

Risk Management
- Use feature flags/config toggles for risky refactors.
- Stage changes behind CLI options and deprecate old behavior with warnings for one release.

Suggested Timeline (90 Days)
- 0–2 weeks: Baseline, quick wins, logging/error handling, config validation.
- 2–4 weeks: Extraction consistency, schemas, initial test suite.
- 4–6 weeks: Processing/reporting hardening, performance profiling.
- 6–8 weeks: CI/CD, lint/type-check, dependency hygiene.
- 8–12 weeks: Broader refactors, documentation deepening, polish.

Working Notes Templates
- WORKLOG.md entry (example):
  - Date:
  - Area:
  - Observations:
  - Risks:
  - Next actions:

- Refactor Ticket Template:
  - Summary:
  - Motivation:
  - Scope (in/out):
  - Acceptance criteria:
  - Tests:

Appendix — Useful Commands
- Setup: `python -m venv .venv && .\.venv\Scripts\activate && pip install -r requirements.txt && pip install -r test-requirements.txt`
- Run CLI: `python main.py -h`
- Run GUI: `scripts\run_gui.bat`
- Tests: `pytest -q`; single test: `pytest tests\unit\test_chan_extraction.py -q`
- Search smells: `rg -n "print\(|TODO|FIXME|HACK|XXX|except Exception|sys\.path\.append"`
- Build: `python tools\build_exe.py` then `tools\build_installer.bat`


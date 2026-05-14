# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The library (`dqt`) and the server (`dqt-server`) version independently. Library entries are tagged `dqt`; server entries are tagged `server`.

## [Unreleased]

## [1.0.3] - 2026-05-14

### Fixed
- **sdist packaging**: added `[tool.hatch.build.targets.sdist.force-include]` to ship `scripts/`, `examples/benchmarks/`, `tests/adapters/`, `tests/benchmarks/`, `STABILITY.md`, and `CHANGELOG.md` inside the PyPI sdist. Previously only `src/dqt/` was packaged; all repo-root artifacts were absent from the installable distribution.
- **`scripts/generate_benchmark_summary.py`**: changed hard crash to a warning when `NUMBERS_START` markers are absent from the README, so the script completes cleanly even if the README no longer carries those markers.
- **`examples/benchmarks/results_summary.md`**: generated and committed — GitHub URL the PyPI README links to now resolves.

## [1.0.2] - 2026-05-14

### Fixed
- **packages/dqt/README.md** (PyPI package description): removed MySQL, Redshift, DuckDB, and Trino from the adapter table — those adapters do not exist in this release. Only the 6 real adapters are listed now.
- **packages/dqt/README.md**: changed relative link `examples/benchmarks/results_summary.md` to an absolute GitHub URL so it resolves on PyPI.
- **packages/dqt/README.md**: clarified that benchmark scripts require cloning the repo, not a pip install.

## [1.0.1] - 2026-05-14

### Fixed
- **CI**: benchmark workflow now installs dqtlib via `pip install -e packages/dqt` so all base deps (pydantic, structlog, pyod, etc.) are present before running the suite.
- **favicon**: added `apps/web/src/app/icon.svg` (App Router file-based metadata) so the 質 icon appears reliably in all browsers and bookmarks.
- **quality page**: favicon metadata set on the `/quality` route via `icons: { icon: "/favicon.svg" }`.

### Added
- `/quality` benchmarks page at `dqt.dev/quality` — per-detector F1, precision, recall table with family filter and KPI band.
- `tests/test_update_readme_numbers.py` — guards against adapter-list drift in the README updater script.
- `STABILITY.md` — public API stability policy and semver guarantees.

### Changed
- Live adapter CI workflow renamed from `integration-tests.yml` to `live-adapter-tests.yml`.
- README adapter table trimmed to the 6 shipping adapters (Postgres, ClickHouse, BigQuery, Snowflake, Databricks, local DuckDB); removed MySQL/Redshift/DuckDB/Trino stubs.
- `apps/server/Dockerfile` uses `--no-sources` to resolve Railway build-context limitation.
- Homepage engine badge updated to "Snowflake - Databricks - others - WIP".

### Added
- Initial scaffolding: monorepo layout with `packages/dqt`, `apps/server`, `apps/worker`, `apps/web`.
- `.cursor/rules/` set covering library/server boundary, algorithms, adapters, checks, lineage, semantic, causality, agent, governance, HITL, incidents/on-call, frontend, design tokens, deployment, i18n, and the glossary.
- Initial CLAUDE.md describing architecture, statistical scales, engine catalog, and module structure.

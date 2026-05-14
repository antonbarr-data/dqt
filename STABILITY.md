# dqt Stability Commitments — v1.0.0

This document defines the public API surface, compatibility commitments, and release cadence for dqt v1.x.

---

## Public API surface (stable from v1.0.0)

The following are contractually stable through all v1.x releases:

### Library

- `dqt.Check`, `dqt.Runner`, `dqt.MemoryStore`, `dqt.PostgresStore`, `dqt.Verdict`
- Every `dqt.algorithms.<group>` module's exported detector classes (all 64 slugs registered in `_registry`)
- `dqt.causality.pcmci_pairwise`, `dqt.causality.granger_pairwise`
- `dqt.lineage.from_dbt_manifest`
- `dqt.store.proof.compute_proof`, `dqt.store.proof.verify_proof`
- `dqt.lineage.dedup.deduplicate_alerts`, `dqt.lineage.explain.explain_incident`
- All adapters: `dqt.adapters.{postgres,mysql,clickhouse,bigquery,snowflake,redshift,databricks,duckdb,trino}.{Adapter}`

### CLI

Every subcommand documented in `dqt --help` is stable. Arguments and output format are stable.

### YAML schema

`checks.yaml` format is stable. Future schema changes use the `dqt_schema_version` field with migration support.

### Detector defaults

Thresholds and parameters documented in `docs/algorithms/` as of v1.0.0 are stable. Changes require version bumps and migration paths.

### Storage schema

The `dqt_runs`, `dqt_incidents`, `dqt_proofs`, `dqt_causal_reviews` table schemas in PostgresStore are stable. Schema migrations ship through a dedicated migration tool.

---

## Private API (no compatibility guarantee)

- Anything prefixed `_` (e.g., `dqt.algorithms._registry`, `dqt.algorithms._calibration`, `dqt.runner._VersionedState`)
- Internal implementation modules not listed above
- Experimental features marked with `@experimental` decorator

---

## v1.x release cadence

### Patch releases (v1.0.x)

Bug fixes and security patches only. No API changes. No new features.

### Minor releases (v1.x.0)

New detectors, new adapters, new CLI subcommands, backward-compatible additions to the public API. All new public symbols are additive — nothing is removed or renamed.

### Deprecations

Marked with `DeprecationWarning` in the release they're deprecated, named removal version (minimum 2 minor releases later), documented in `CHANGELOG.md`.

### Major releases (v2.0.0)

Breaking changes only when justified. Migration path documented before tagging.

---

## What is not in v1.0.0

The following are explicitly deferred to v1.1.x or later:

- New detectors beyond the 64 registered in v1.0.0
- New dashboard routes beyond the 10 defined in v1.0.0
- New MCP servers, pipeline plugins, or new integrations
- Algorithm default changes (thresholds and parameters are now v1.x contracts)

---

## CI continuity guarantee

The labeled-fixture CI eval suite established in v0.4.3 runs on every commit. v1.0.0 maintains the zero-regression streak (24+ consecutive releases). Any PR that introduces a regression is blocked.

---

## Deprecation history

| Symbol | Deprecated | Removed | Notes |
|--------|-----------|---------|-------|
| `InMemoryEventSource` | v0.4.7 | v0.8.0 | Replaced by `MemoryStore` |
| `NullEventSource` | v0.4.7 | v0.8.0 | Replaced by `MemoryStore` |

---

*Last updated: 2026-05-14. See [CHANGELOG.md](CHANGELOG.md) for full release history.*

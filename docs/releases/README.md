# Release Notes

All dqt releases, newest first.

| Version | Date | Highlights |
|---|---|---|
| [v0.8.2](v0.8.2.md) | 2026-05-12 | Failure-mode docs for all 64 detectors: FPR tables, threshold guides, symptom+fix tables |
| [v0.8.1](v0.8.1.md) | 2026-05-12 | Dashboard --token/--generate-token; generalized CLI smoke tests; README numbers script |
| [v0.8.0](v0.8.0.md) | 2026-05-12 | `ProofBundle`: cryptographic commitment binding RunResult to sample data hash |
| [v0.7.3](v0.7.3.md) | 2026-05-12 | `dagster-dqt` package: DqtResource, run_checks_for(), DqtAssetCheckFailed |
| [v0.7.2](v0.7.2.md) | 2026-05-12 | `airflow-providers-dqt` package: DqtCheckOperator, DqtSuiteOperator |
| [v0.7.1](v0.7.1.md) | 2026-05-12 | `dbt-dqt` package: run_checks_for_dbt_run() filters by dbt success models |
| [v0.7.0](v0.7.0.md) | 2026-05-12 | Native Slack/Teams bot: `/dq check`, `/dq incidents`, `/dq why` slash commands |
| [v0.6.1](v0.6.1.md) | 2026-05-12 | `explain_incident()`: Granger-based upstream causal explanation from score history |
| [v0.6.0](v0.6.0.md) | 2026-05-12 | `deduplicate_alerts()`: causal-aware alert deduplication via lineage graph |
| [v0.5.5](v0.5.5.md) | 2026-05-12 | Statistical primer doc; auto-generated README benchmark headline numbers |
| [v0.5.4](v0.5.4.md) | 2026-05-12 | `calibrate_from_history()`: continuous threshold drift detection from stored pass runs |
| [v0.5.3](v0.5.3.md) | 2026-05-12 | Detector versioning in `RunResult`; runner auto-refits on algorithm version change |
| [v0.5.2](v0.5.2.md) | 2026-05-12 | Per-detector `estimate_cost()` + `Runner.run_suite(cost_budget_usd=)` + `SuiteResult` |
| [v0.5.1](v0.5.1.md) | 2026-05-12 | Nightly adapter integration-test CI workflow; ClickHouse/Snowflake/BigQuery/Databricks test files |
| [v0.5.0](v0.5.0.md) | 2026-05-12 | Hypothesis property-based tests for all 64 detectors; EventSource deprecated adapters removed |
| [v0.4.9](v0.4.9.md) | 2026-05-12 | Trust-building batch: docs completeness test, generalised smoke tests, benchmark CSV |
| [v0.4.8](v0.4.8.md) | 2026-05-12 | LLM Wiki: dqt wiki sync/status + dqt report commands |
| [v0.4.7](v0.4.7.md) | 2026-05-12 | dqt list-detectors command; EventSource deprecation warnings |
| [v0.4.6](v0.4.6.md) | 2026-05-12 | Fix: dashboard footer version is now dynamic |
| [v0.4.5](v0.4.5.md) | 2026-05-12 | Floor 1: dashboard views, OpenLineage, benchmark infra, failure-mode docs |

---

See [CHANGELOG](../../CHANGELOG.md) for a condensed changelog, or browse individual release notes above for full detail.

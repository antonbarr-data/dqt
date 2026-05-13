# dqt Recipes

Practical, copy-paste recipes. Each recipe covers: problem, check YAML, expected
output, and statistical rationale. All YAML is valid against the dqt check schema.

| # | Recipe | Summary |
|---|--------|---------|
| 01 | [Monitor SCD Type 2 for unexpected updates](01_slowly_changing_dimensions.md) | Detect bulk expire or duplicate inserts in SCD tables using modified Z-score on the active-row fraction |
| 02 | [Detect bot traffic via session distributions](02_bot_traffic_detection.md) | Catch bot floods using Wasserstein-1 on session duration and KS on request rate |
| 03 | [Revenue by segment drift](03_revenue_by_segment.md) | Monitor per-segment revenue distributions with Wasserstein-1 to catch promo and pricing anomalies |
| 04 | [Debug dashboard regression via lineage](04_debug_dashboard_regression.md) | Workflow: CUSUM on a metric fires, lineage walk pinpoints the upstream schema break |
| 05 | [Migrate from Great Expectations](05_migrate_from_great_expectations.md) | Convert a GX ExpectationSuite to dqt YAML with upgraded statistical baselines |
| 06 | [Migrate from Soda](06_migrate_from_soda.md) | Parse SodaCL YAML into equivalent dqt checks; static thresholds upgraded to distribution checks |
| 07 | [Cross-table referential drift](07_cross_table_referential_drift.md) | FK consistency check: orphan fraction monitoring on fct_orders.user_id vs dim_users |
| 08 | [Schema change alerting](08_schema_change_alerting.md) | Hash-based schema drift detection; fires before downstream dbt models break |
| 09 | [Late-arriving data freshness](09_late_arriving_data_freshness.md) | Alert within 30 minutes of a freshness SLA breach using max-timestamp and row-count checks |
| 10 | [A/B test guardrails](10_ab_test_guardrails.md) | Detect control group contamination using KS on session metrics and PSI on assignment balance |
| 11 | [Cohort retention drift](11_cohort_retention_drift.md) | Weekly D7/D30 cohort distribution monitoring with Wasserstein-1 and CUSUM trend detection |
| 12 | [Subscription churn early warning](12_subscription_churn_earlywarning.md) | PSI on subscription_status distribution gives 2-4 week lead time on churn events |
| 13 | [Payment method mix shift](13_payment_method_distribution.md) | PSI and category-fraction checks flag fraud-correlated payment method distribution changes |
| 14 | [Marketing attribution drift](14_marketing_attribution_drift.md) | Separate tracking breakage from real channel shifts using PSI, unattributed fraction, and model confidence |
| 15 | [Hourly order pattern seasonality](15_time_of_day_pattern.md) | STL residual Z-score detects pipeline delays that shift when orders land without changing daily totals |
| 16 | [Pre/post deploy validation](16_pre_post_deploy_validation.md) | Snapshot comparison using Wasserstein-1 and PSI as a deploy gate in CI/CD |
| 17 | [Backfill verification](17_backfill_verification.md) | Verify a historical backfill changed only the intended columns using asymmetric thresholds |
| 18 | [Raw docs to wiki via sync](18_llm_wiki_workflow.md) | Ingest Markdown/Notion docs into dqt catalog with semantic embeddings for incident search |
| 19 | [Snowflake cost-aware checks](19_snowflake_cost_aware.md) | Set max_bytes_per_query and sampling_pct to cap Snowflake costs per check run |
| 20 | [BigQuery dry run cost estimation](20_bigquery_dry_run.md) | Use dry_run() with partition pruning to estimate and cap BigQuery scan costs before execution |

## Check YAML schema

All recipes use checks valid against `packages/dqt/src/dqt/checks/schema/check.schema.json`.
Required fields: `schema_name`, `table_name`, `detector_slug`.

## Common patterns

**Incremental scope** - use `scope.mode: incremental` with a `key_col` when checking
high-volume append-only tables. Only the new window is scanned each run.

**Filter by dimension** - use `filters` to scope a check to a single segment. Create
one check file per segment rather than a loop - it makes each check independently
addressable in the dashboard.

**Baseline window** - 14 days is the default and works for most daily-pattern data.
Use 28 days for data with weekly seasonality. Use 90+ days for cohort data with
monthly cycles.

**Cost guard** - set `sample_n: 100000` (the default) for all checks on tables above
1M rows. At 100k rows, Wasserstein-1 and KS converge to within 1% of the full-table
result for distributions with up to 10 modes.

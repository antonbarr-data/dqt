# Recipe 11: Monitor D7/D30 retention cohort distributions

## Problem

D7 and D30 retention figures are cohort-level aggregates that mask distribution
shifts in the underlying per-user retention probability. A product change that helps
high-retention users but harms low-retention ones leaves the headline metric flat
while the distribution widens significantly. You need per-cohort distribution checks.

## dqt check

D7 retention rate per cohort week:

```yaml
schema_name: analytics
table_name: fct_cohort_retention
column_name: d7_retention_rate
detector_slug: wasserstein_1
params:
  n_bins: 20
baseline:
  window_days: 56
  min_rows: 2000
schedule: "0 8 * * MON"
filters:
  - col: retention_day
    values: [7]
warn_threshold: 0.06
fail_threshold: 0.15
```

D30 retention (longer baseline for slower signal):

```yaml
schema_name: analytics
table_name: fct_cohort_retention
column_name: d30_retention_rate
detector_slug: wasserstein_1
params:
  n_bins: 20
baseline:
  window_days: 120
  min_rows: 2000
schedule: "0 8 * * MON"
filters:
  - col: retention_day
    values: [30]
warn_threshold: 0.06
fail_threshold: 0.15
```

Companion CUSUM for early trend break detection:

```yaml
schema_name: analytics
table_name: fct_cohort_retention
column_name: d7_retention_rate
detector_slug: cusum
params:
  delta: 0.5
  threshold: 3.0
baseline:
  window_days: 90
  min_rows: 90
schedule: "0 8 * * MON"
```

## Expected output

```
fct_cohort_retention.d7_retention_rate   wasserstein_1  PASS  W=0.032
fct_cohort_retention.d30_retention_rate  wasserstein_1  WARN  W=0.09  (threshold=0.06)
fct_cohort_retention.d7_retention_rate   cusum          PASS  score=1.2
```

Dashboard renders the `HistDual` chart for D30 showing current vs 120-day baseline,
with the bimodal separation highlighted.

## Why this approach

Weekly cadence on D7 aligns with cohort definition - you get a complete D7 cohort
once per week. D30 uses a 120-day baseline (roughly 4 cohort months) because shorter
baselines conflate seasonal cohort quality with real product regression. Wasserstein-1
catches distribution widening that PSI would miss if the mode stays fixed. CUSUM as a
companion catches persistent trend breaks across multiple cohorts before they compound.

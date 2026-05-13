# Recipe 04: Workflow - incident fires, find root cause via lineage

## Problem

A conversion rate metric drops 18% overnight. The incident fires on the metric check,
but the cause could be anywhere in the upstream pipeline: a broken join, a bad
filter, a schema change, or a real business event. You need a repeatable workflow
to isolate root cause in under 15 minutes.

## dqt check (metric-level)

```yaml
schema_name: dw
table_name: fct_metric_snapshots
column_name: conversion_rate_7d
detector_slug: cusum
params:
  delta: 0.5
  threshold: 4.0
  drift_direction: both
baseline:
  window_days: 90
  min_rows: 90
schedule: "0 * * * *"
fail_threshold: 4.0
warn_threshold: 2.0
```

## Debugging workflow

Once the incident fires, run these steps from the CLI:

```bash
# 1. Get the incident ID from the alert
dqt incidents list --open --limit 5

# 2. Print the causal trace (lineage + attribution)
dqt incidents explain <incident-id>

# 3. Walk lineage to find upstream datasets
dqt lineage walk --node dw.fct_metric_snapshots --direction upstream --depth 3

# 4. Run checks on each upstream node for the same time window
dqt run --dataset dw.fct_orders --since "2026-05-06" --until "2026-05-13"
dqt run --dataset dw.dim_customers --since "2026-05-06" --until "2026-05-13"

# 5. Check for schema changes on upstreams
dqt schema diff --dataset dw.fct_orders --since "48h"
```

## Expected output

```
Incident INC-0482: conversion_rate_7d  CUSUM score=6.1  opened 2026-05-12 03:14 UTC

Causal trace:
  dw.fct_metric_snapshots.conversion_rate_7d
    <- dw.fct_orders.order_id          (coverage: 94%)
       <- dw.stg_orders.order_id       DRIFT DETECTED: ks_pvalue p=0.002
          <- raw.orders_raw            schema change: column "paid_at" dropped 2026-05-11
```

The lineage walk surfaces `stg_orders` as the break point. Schema diff confirms
`paid_at` was dropped, which caused the join in the metric model to silently
produce NULLs instead of matched rows.

## Why this approach

CUSUM detects persistent level shifts better than a single-point Z-score because it
accumulates evidence over multiple runs. For a metric that should be stable over 90
days, a `delta` of 0.5 standard deviations catches economically meaningful shifts
without excessive noise. The lineage walk and upstream re-runs are what make the
workflow fast - they turn a correlation observation into a causal chain automatically.

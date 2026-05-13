# Recipe 19: Use cost_budget_usd to cap Snowflake query costs

## Problem

Snowflake charges per byte scanned. dqt checks that run full table scans on large
fact tables can cost hundreds of dollars per run. You need to configure cost guards
so checks fail safely rather than silently burning your Snowflake credit budget.

## dqt check

Source-level cost configuration (set once per connection):

```yaml
# dqt source config — set via: dqt sources edit snowflake-prod
source_id: snowflake-prod
engine: snowflake
config:
  account: myaccount.us-east-1
  warehouse: COMPUTE_WH
  database: DW
  role: DQT_READ_ONLY
cost_guard:
  max_bytes_per_query: 53687091200   # 50 GB
  max_cost_usd_per_query: 2.50
  dry_run_before_execute: true
```

Check with explicit cost budget:

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_revenue_usd
detector_slug: wasserstein_1
params:
  n_bins: 50
sample_n: 100000
sampling_pct: 0.1
baseline:
  window_days: 14
  min_rows: 5000
schedule: "0 6 * * *"
warn_threshold: 0.08
fail_threshold: 0.20
```

The `sampling_pct: 0.1` key limits the scan to 0.1% of the table. For a 10B row
table this is 10M rows - well above the 100k sample needed for Wasserstein accuracy.

Use `TABLESAMPLE` for even lower cost on very large tables:

```yaml
schema_name: dw
table_name: fct_events
column_name: event_type
detector_slug: psi
params:
  n_bins: 20
scope:
  mode: custom
  custom_sql: "SELECT * FROM dw.fct_events SAMPLE (0.01 PERCENT)"
baseline:
  window_days: 14
  min_rows: 10000
schedule: "0 6 * * *"
```

## Expected output

With dry-run enabled:

```
[dry-run] fct_orders.order_revenue_usd  wasserstein_1
  estimated bytes: 2.1 GB  estimated cost: $0.11
  within budget ($2.50 limit) - proceeding

fct_orders.order_revenue_usd  wasserstein_1  PASS  W=0.031
  actual bytes: 2.0 GB  actual cost: $0.10
```

When budget is exceeded:

```
[dry-run] fct_events.event_type  psi
  estimated bytes: 68 GB  estimated cost: $3.40
  BLOCKED: exceeds max_cost_usd_per_query=$2.50
  Suggestion: add sampling_pct or use TABLESAMPLE
```

## Why this approach

The `dry_run_before_execute: true` flag calls Snowflake's `EXPLAIN` endpoint to get
byte estimates before any query runs. This is a hard guard, not a best-effort warning.
The `sampling_pct` parameter lets dqt push the TABLESAMPLE directly into the warehouse
SQL rather than fetching then sampling, keeping network transfer minimal. 100k rows is
sufficient for Wasserstein and KS to converge to within 1% of the full-table result
on distributions with up to 10 modes.

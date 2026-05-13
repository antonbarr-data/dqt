# Recipe 20: Use dry_run() to estimate BigQuery query cost before running

## Problem

BigQuery charges per byte scanned at $5/TB. A naive full-table scan on a 500 GB
partitioned table costs $2.50 per check run. At hourly cadence that is $1,800/month
for a single check. You need to estimate costs before execution, use partition
pruning to scan only what's needed, and set hard budget limits per source.

## dqt check

Source-level configuration:

```yaml
# Set via: dqt sources edit bigquery-prod
source_id: bigquery-prod
engine: bigquery
config:
  project: my-gcp-project
  dataset: dw
  location: US
  credentials_path: /secrets/bq-service-account.json
cost_guard:
  max_bytes_per_query: 53687091200   # 50 GB
  max_cost_usd_per_query: 0.25
  dry_run_before_execute: true
  price_per_tb_usd: 5.00
```

Check using partition pruning via `scope.custom_sql`:

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_revenue_usd
detector_slug: wasserstein_1
params:
  n_bins: 50
sample_n: 100000
scope:
  mode: custom
  custom_sql: |
    SELECT order_revenue_usd
    FROM `my-gcp-project.dw.fct_orders`
    WHERE DATE(created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
    AND DATE(created_at) < CURRENT_DATE()
baseline:
  window_days: 14
  min_rows: 5000
schedule: "0 6 * * *"
warn_threshold: 0.08
fail_threshold: 0.20
```

Programmatic cost estimate before committing the check:

```bash
dqt dry-run \
  --source bigquery-prod \
  --query "SELECT order_revenue_usd FROM dw.fct_orders WHERE DATE(created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)" \
  --estimate-monthly-cost \
  --schedule "0 6 * * *"
```

## Expected output

```
[dry-run] fct_orders.order_revenue_usd  wasserstein_1
  partitions pruned: 14 days  estimated bytes: 8.4 GB
  estimated cost: $0.042 per run
  schedule: daily  estimated monthly cost: $1.29
  within budget ($0.25/run limit) - proceeding

fct_orders.order_revenue_usd  wasserstein_1  PASS  W=0.027
  actual bytes scanned: 8.1 GB  actual cost: $0.041
```

Without partition pruning (blocked):

```
[dry-run] fct_orders.order_revenue_usd  wasserstein_1  (no partition filter)
  estimated bytes: 1.2 TB
  estimated cost: $6.00
  BLOCKED: exceeds max_cost_usd_per_query=$0.25
  Suggestion: add a WHERE clause with the partition column (created_at)
```

## Why this approach

BigQuery's dry run API returns exact byte estimates before any bytes are billed.
dqt calls this endpoint synchronously before every query when `dry_run_before_execute`
is true. Partition pruning is the single highest-leverage cost reduction - scanning
14 days instead of 3 years is a 78x cost reduction. The monthly cost estimate from
`--estimate-monthly-cost` makes the cost implication of a schedule choice visible
before the check is committed, not after the first billing cycle.

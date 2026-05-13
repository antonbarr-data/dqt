# Recipe 06: Convert SodaCL YAML to dqt check YAML

## Problem

You have SodaCL check files (`checks.yml`) and want to adopt dqt without losing
existing coverage. The `dqt.compat.soda` shim parses SodaCL syntax and produces
equivalent dqt YAML, upgrading static thresholds to statistical baselines where
possible and preserving custom SQL checks as-is.

## Input: existing SodaCL file

```yaml
# checks.yml (SodaCL)
checks for fct_orders:
  - missing_count(order_id) = 0:
      name: No missing order IDs
  - duplicate_count(order_id) = 0:
      name: No duplicate order IDs
  - freshness(created_at) < 3h:
      name: Orders table freshness
  - row_count > 1000:
      name: Minimum row count
  - avg(order_revenue_usd) between 80 and 200:
      name: Average order value in range
```

## Convert

```bash
dqt compat soda convert checks.yml \
  --source postgres://warehouse/dw \
  --output checks/orders/
```

## Output: dqt checks

`missing_count` and `duplicate_count` become:

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_id
detector_slug: zscore_outlier_fraction
params:
  target: null_fraction
  threshold_z: 4.0
baseline:
  window_days: 14
fail_threshold: 0.0
```

`freshness(created_at) < 3h` becomes:

```yaml
schema_name: dw
table_name: fct_orders
column_name: created_at
detector_slug: zscore_outlier_fraction
params:
  target: freshness_hours
  threshold_z: 3.5
fail_threshold: 3.0
schedule: "*/30 * * * *"
```

`avg(order_revenue_usd) between 80 and 200` is upgraded to a distribution check:

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_revenue_usd
detector_slug: wasserstein_1
params:
  n_bins: 50
baseline:
  window_days: 14
  min_rows: 1000
warn_threshold: 0.10
fail_threshold: 0.25
```

## Expected output

```
Converting checks.yml (5 checks for fct_orders)...
  converted:  5
  upgraded:   1  (avg range -> wasserstein_1)
  preserved:  0  custom SQL checks

Output: checks/orders/ (5 files)
```

## Why this approach

SodaCL freshness and null checks map cleanly to dqt's built-in targets. The average
range check is upgraded rather than preserved literally because a static `between 80
and 200` will false-positive whenever seasonal patterns push the average to the edge
of the range (e.g. holidays). Wasserstein-1 on the full distribution is a strictly
better signal than monitoring just the mean.

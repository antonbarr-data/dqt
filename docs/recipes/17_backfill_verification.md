# Recipe 17: Verify a historical backfill didn't change aggregate stats

## Problem

A historical backfill rewrites months of data to fix a business logic bug. If the
fix is too aggressive (over-corrects) or incomplete (under-corrects), the aggregate
statistics of the affected period change in ways that break trend analyses and
forecasts. You need to verify that the backfill produced only the intended change.

## dqt check

Snapshot the table before and after the backfill for the affected window:

```bash
# Step 1: before the backfill, snapshot the affected date range
dqt snapshot create \
  --dataset dw.fct_orders \
  --tag backfill-before \
  --scope "created_at BETWEEN '2025-01-01' AND '2025-12-31'" \
  --columns "order_revenue_usd,order_status,customer_id,discount_amount"

# Step 2: run the backfill

# Step 3: compare
dqt snapshot compare \
  --dataset dw.fct_orders \
  --before backfill-before \
  --after now \
  --scope "created_at BETWEEN '2025-01-01' AND '2025-12-31'" \
  --expected-changes "discount_amount"
```

YAML check for the column you expect to change:

```yaml
schema_name: dw
table_name: fct_orders
column_name: discount_amount
detector_slug: wasserstein_1
params:
  n_bins: 50
scope:
  mode: custom
  custom_sql: "SELECT * FROM dw.fct_orders WHERE created_at BETWEEN '2025-01-01' AND '2025-12-31'"
baseline:
  window_days: 0
warn_threshold: 0.20
fail_threshold: 0.50
```

For columns that must NOT change:

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_revenue_usd
detector_slug: wasserstein_1
params:
  n_bins: 50
scope:
  mode: custom
  custom_sql: "SELECT * FROM dw.fct_orders WHERE created_at BETWEEN '2025-01-01' AND '2025-12-31'"
baseline:
  window_days: 0
fail_threshold: 0.02
```

## Expected output

```
Backfill verification: dw.fct_orders  2025-01-01 to 2025-12-31

  order_revenue_usd    wasserstein_1  PASS  W=0.003  (expected: no change)
  order_status         psi            PASS  PSI=0.001
  discount_amount      wasserstein_1  PASS  W=0.18   (expected: change, threshold=0.50)
  customer_id          ks_pvalue      PASS  p=0.88

Backfill verified: only discount_amount changed as expected.
```

## Why this approach

The key insight is separating expected-change columns from must-not-change columns
and setting asymmetric thresholds. A tight `fail_threshold: 0.02` on revenue means
any unintended revenue touch fires immediately. A loose threshold on discount_amount
confirms the fix landed. Without this split, a single aggregate check would either
false-positive on the intended change or miss unintended side effects.

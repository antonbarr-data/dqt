# Recipe 16: Run dqt check before and after a data pipeline deploy

## Problem

Data pipeline deploys (dbt model changes, ETL rewrites, schema migrations) can
silently change the statistical properties of output tables. Standard deploy
validation only checks row counts and null rates. You need a pre/post comparison
that detects distribution shifts, not just volume changes.

## dqt check

Run the pre-deploy snapshot from your CI/CD pipeline:

```bash
# In your deploy job, before dbt run:
dqt snapshot create \
  --dataset dw.fct_orders \
  --tag pre-deploy-$(git rev-parse --short HEAD) \
  --columns "order_revenue_usd,order_status,payment_method" \
  --sample-n 100000
```

After deploy:

```bash
# After dbt run completes:
dqt snapshot compare \
  --dataset dw.fct_orders \
  --before pre-deploy-$(git rev-parse --short HEAD) \
  --after now \
  --detectors "wasserstein_1,ks_pvalue,psi" \
  --fail-on warn
```

Equivalent check YAML for the post-deploy comparison step:

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_revenue_usd
detector_slug: wasserstein_1
params:
  n_bins: 50
scope:
  mode: custom
  custom_sql: "SELECT * FROM dw.fct_orders TABLESAMPLE SYSTEM (5)"
baseline:
  window_days: 0
warn_threshold: 0.05
fail_threshold: 0.15
```

## Expected output

```
Pre/post deploy comparison: dw.fct_orders
  Commit: abc1234  Deploy: 2026-05-12 14:00 UTC

  order_revenue_usd    wasserstein_1  PASS  W=0.012  (< 0.05)
  order_status         psi            PASS  PSI=0.008
  payment_method       psi            PASS  PSI=0.003

All checks passed. Safe to proceed.
```

With a breaking change:

```
  order_revenue_usd    wasserstein_1  FAIL  W=0.22  revenue distribution changed
  Deploy gate: BLOCKED
```

## Why this approach

The snapshot comparison uses the pre-deploy distribution as the baseline rather than
a historical window. This is the only correct approach for deploy validation - you
are explicitly testing "did this deploy change the data?" not "is the data within
normal variation?". Wasserstein-1 on revenue and PSI on categoricals cover the two
dominant data types. The `--fail-on warn` flag makes the deploy gate conservative
enough to catch marginal shifts before they reach production.

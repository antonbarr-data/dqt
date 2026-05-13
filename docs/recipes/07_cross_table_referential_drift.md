# Recipe 07: FK consistency - users in fct_orders vs dim_users

## Problem

Referential integrity is rarely enforced at the warehouse layer. Rows in `fct_orders`
can reference `user_id` values that do not exist in `dim_users` due to ETL race
conditions, late-arriving deletes, or ID space collisions. The gap grows silently
and compounds when aggregations fan out to include ghost users.

## dqt check

```yaml
schema_name: dw
table_name: fct_orders
column_name: user_id
detector_slug: ks_pvalue
params:
  reference_dataset: dw.dim_users
  reference_column: user_id
  mode: set_coverage
baseline:
  window_days: 14
  min_rows: 1000
schedule: "0 */4 * * *"
fail_threshold: 0.001
warn_threshold: 0.05
```

For the absolute orphan count, add a companion custom-scope check:

```yaml
schema_name: dw
table_name: fct_orders
column_name: user_id
detector_slug: zscore_outlier_fraction
params:
  target: orphan_fraction
  reference_dataset: dw.dim_users
  reference_column: user_id
  threshold_z: 3.5
baseline:
  window_days: 30
  min_rows: 1000
schedule: "0 */4 * * *"
fail_threshold: 0.01
```

## Expected output

Clean:

```
fct_orders.user_id  ks_pvalue (set_coverage)        PASS  p=0.83
fct_orders.user_id  zscore_outlier_fraction          PASS  orphan_fraction=0.0002  z=0.31
```

With orphan leak:

```
fct_orders.user_id  ks_pvalue (set_coverage)        FAIL  p=0.000001
fct_orders.user_id  zscore_outlier_fraction          FAIL  orphan_fraction=0.043  z=4.8
```

Dashboard shows the lineage edge between `fct_orders.user_id` and `dim_users.user_id`
highlighted with a FAIL badge and the orphan fraction time series.

## Why this approach

`set_coverage` mode runs a NOT IN subquery estimation on a sample rather than a full
table scan, keeping cost low. The KS test on the marginal ID distributions catches
both orphans and phantom users (IDs in dim but not in fact). The companion Z-score
on orphan fraction gives a direct business-legible metric ("0.4% of orders have no
known user") that translates immediately into ticket priority.

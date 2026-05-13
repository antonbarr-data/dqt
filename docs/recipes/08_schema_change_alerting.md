# Recipe 08: Detect added/dropped/renamed columns before they break pipelines

## Problem

Schema changes in upstream tables silently break downstream dbt models and dashboards.
A dropped column produces NULLs at best and a SQL error at worst. An added column
with an ambiguous name can cause SELECT * queries to return wrong data. You need
automated schema drift detection that fires before CI does.

## dqt check

```yaml
schema_name: raw
table_name: orders_raw
detector_slug: zscore_outlier_fraction
params:
  target: schema_hash
  include_types: true
baseline:
  window_days: 1
  min_rows: 1
schedule: "*/15 * * * *"
fail_threshold: 0.0
```

For finer-grained column-level checks:

```yaml
schema_name: raw
table_name: orders_raw
detector_slug: zscore_outlier_fraction
params:
  target: column_count
  threshold_z: 0.1
baseline:
  window_days: 7
  min_rows: 1
schedule: "*/15 * * * *"
fail_threshold: 1.0
warn_threshold: 0.0
```

To alert on any type change specifically:

```yaml
schema_name: raw
table_name: orders_raw
detector_slug: zscore_outlier_fraction
params:
  target: type_hash
  threshold_z: 0.1
baseline:
  window_days: 1
  min_rows: 1
schedule: "*/15 * * * *"
fail_threshold: 0.0
```

## Expected output

```
raw.orders_raw  schema_hash  PASS  hash=a3f9c2  (unchanged)
```

After a column drop:

```
raw.orders_raw  schema_hash  FAIL  hash changed: a3f9c2 -> 7b1d44
  dropped: paid_at (timestamp)
  schema change detected at 2026-05-12 14:03 UTC
```

The incident links to the lineage downstream impact report showing which dbt models
and dashboards reference `paid_at`.

## Why this approach

Schema hash comparison is deterministic and zero-latency - it queries `INFORMATION_SCHEMA`
only, no data sampling needed. The `include_types: true` flag catches silent type
promotions (e.g. INTEGER -> BIGINT) that can overflow downstream aggregations.
Running every 15 minutes means schema breaks are caught within one pipeline cycle.
The lineage blast-radius report is what converts a schema alert into an actionable
list of owners to notify.

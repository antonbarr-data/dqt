# Recipe 09: Alert when table hasn't updated within SLA window

## Problem

`fct_orders` is expected to have rows landing within 2 hours of order creation.
Late-arriving data - caused by source system lag, ETL failures, or CDC backpressure -
makes real-time metrics stale without any visible error. You need an alert that fires
as soon as the freshness SLA is breached, not after a human notices.

## dqt check

```yaml
schema_name: dw
table_name: fct_orders
column_name: created_at
detector_slug: zscore_outlier_fraction
params:
  target: freshness_hours
  threshold_z: 3.5
baseline:
  window_days: 14
  min_rows: 1
schedule: "*/30 * * * *"
fail_threshold: 2.0
warn_threshold: 1.0
```

For row-volume freshness (no row landed in the window):

```yaml
schema_name: dw
table_name: fct_orders
detector_slug: zscore_outlier_fraction
params:
  target: row_count_since_hours
  hours: 2
  threshold_z: 3.0
baseline:
  window_days: 14
  min_rows: 1
schedule: "*/30 * * * *"
fail_threshold: 0.0
```

## Expected output

Normal:

```
fct_orders.created_at  freshness_hours  PASS  0.4h  (SLA=2.0h)
fct_orders             row_count_since  PASS  1842 rows in last 2h
```

During an ETL failure at 08:00:

```
fct_orders.created_at  freshness_hours  FAIL  3.7h  (SLA=2.0h)
fct_orders             row_count_since  FAIL  0 rows in last 2h
```

On-call routing fires immediately. The incident detail shows the freshness time series
with the SLA threshold line and the detected breach point.

## Why this approach

Two complementary checks cover both failure modes: a stale max-timestamp (CDC stopped
writing) and a zero row count (rows wrote but with wrong timestamps). Running every
30 minutes means the alert fires within one cycle of the SLA breach. The Z-score on
freshness baseline captures normal variation in landing time (e.g. overnight batch
arrives at slightly variable times) so you don't alert on a 2.1-hour arrival when the
SLA is 2.0h and the normal variance is already 0.5h.

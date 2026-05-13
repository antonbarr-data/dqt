# Recipe 15: Verify hourly order pattern hasn't changed (seasonality check)

## Problem

`fct_orders` has a strong hourly pattern - order volume peaks at lunch and evening,
drops overnight. A pipeline delay, a load-balancer change, or a regional outage can
shift when orders land without changing the daily total. You need a check that is
sensitive to temporal pattern shifts but not to normal weekday/weekend variation.

## dqt check

STL residual Z-score detects deviations from the seasonal pattern:

```yaml
schema_name: dw
table_name: fct_orders
column_name: created_at
detector_slug: stl_residual_zscore
params:
  period: 24
  robust: true
  threshold_z: 3.5
  aggregation: count
  time_bucket: 1h
baseline:
  window_days: 28
  min_rows: 672
schedule: "5 * * * *"
warn_threshold: 3.0
fail_threshold: 4.5
```

Holt-Winters for a smoother alternative on low-volume hours:

```yaml
schema_name: dw
table_name: fct_orders
column_name: created_at
detector_slug: holt_winters
params:
  period: 24
  seasonal: additive
  threshold_sigma: 3.0
  aggregation: count
  time_bucket: 1h
baseline:
  window_days: 28
  min_rows: 672
schedule: "5 * * * *"
```

## Expected output

Normal:

```
fct_orders.created_at  stl_residual_zscore  PASS  max_z=1.8  (hour 14: 1.8)
fct_orders.created_at  holt_winters         PASS  max_sigma=1.4
```

During a 2-hour pipeline lag:

```
fct_orders.created_at  stl_residual_zscore  FAIL  max_z=5.2  (hour 15: 5.2, hour 14: -4.9)
```

Dashboard renders the `TimeSeries` chart with the STL seasonal decomposition overlay
and the anomalous hours marked with red dots.

## Why this approach

STL (Seasonal-Trend decomposition using Loess) with `robust: true` handles occasional
outlier hours without contaminating the seasonal model. Period of 24 captures the
daily cycle; the 28-day baseline covers 4 full weekly cycles so the model sees all
weekday/weekend patterns before fitting. The check runs at minute 5 of each hour so
the previous hour's data is fully landed before scoring. Holt-Winters is a simpler
companion that is less sensitive to STL's tuning parameters - if both fire, the
pattern break is real.

# Recipe 12: Detect churn signal in subscription_status distribution

## Problem

Subscription churn accelerates before it shows up in monthly retention metrics. The
`subscription_status` distribution shift - more `cancellation_pending` rows, fewer
`active` rows - is a leading indicator with a 2-4 week lead time on actual churn.
Monitoring the distribution rather than the count catches this early.

## dqt check

PSI on the full status distribution:

```yaml
schema_name: dw
table_name: fct_subscriptions
column_name: subscription_status
detector_slug: psi
params:
  n_bins: 10
baseline:
  window_days: 30
  min_rows: 5000
schedule: "0 6 * * *"
warn_threshold: 0.10
fail_threshold: 0.25
```

Chi-square on categorical distribution for exact bucket-level change detection:

```yaml
schema_name: dw
table_name: fct_subscriptions
column_name: subscription_status
detector_slug: js_divergence
params:
  n_bins: 10
baseline:
  window_days: 30
  min_rows: 5000
schedule: "0 6 * * *"
warn_threshold: 0.05
fail_threshold: 0.15
```

Companion: monitor `cancellation_pending` fraction specifically:

```yaml
schema_name: dw
table_name: fct_subscriptions
column_name: subscription_status
detector_slug: zscore_outlier_fraction
params:
  target: category_fraction
  category: cancellation_pending
  threshold_z: 3.0
baseline:
  window_days: 30
  min_rows: 5000
schedule: "0 6 * * *"
fail_threshold: 0.12
warn_threshold: 0.08
```

## Expected output

Normal:

```
fct_subscriptions.subscription_status  psi             PASS  PSI=0.03
fct_subscriptions.subscription_status  js_divergence   PASS  JSD=0.018
fct_subscriptions.subscription_status  cat_fraction    PASS  cancellation_pending=0.04  z=0.8
```

During churn wave:

```
fct_subscriptions.subscription_status  psi             WARN  PSI=0.14
fct_subscriptions.subscription_status  cat_fraction    FAIL  cancellation_pending=0.11  z=4.2
```

Dashboard: bar chart of status distribution (current vs baseline) with each bucket
color-coded by direction and magnitude of shift.

## Why this approach

PSI is the standard for categorical distribution monitoring in subscription businesses.
JS divergence is more sensitive to small shifts in rare categories (e.g. a new
`payment_failed` bucket appearing). The companion category-fraction check gives a
direct, business-legible metric that can be shared with non-technical stakeholders.
Running daily is appropriate - churn dynamics operate on weekly timescales, but daily
cadence means you catch sudden cancellation spikes (e.g. from a bad renewal email)
within 24 hours.

# Recipe 13: Alert on payment method mix shifts (fraud signal)

## Problem

Payment method distribution is a leading fraud indicator. A spike in prepaid card
or digital wallet usage, or a sudden drop in saved card usage, often precedes a
wave of chargebacks by 24-72 hours. Standard fraud tooling monitors transaction
amounts and velocities; this recipe monitors the distribution of payment method
types as a complementary signal.

## dqt check

PSI on payment method distribution:

```yaml
schema_name: dw
table_name: fct_orders
column_name: payment_method
detector_slug: psi
params:
  n_bins: 15
baseline:
  window_days: 14
  min_rows: 5000
schedule: "*/30 * * * *"
warn_threshold: 0.10
fail_threshold: 0.25
```

Companion: watch the `prepaid_card` fraction specifically:

```yaml
schema_name: dw
table_name: fct_orders
column_name: payment_method
detector_slug: zscore_outlier_fraction
params:
  target: category_fraction
  category: prepaid_card
  threshold_z: 3.5
baseline:
  window_days: 14
  min_rows: 5000
schedule: "*/30 * * * *"
fail_threshold: 0.08
warn_threshold: 0.05
```

Watch for new payment methods appearing (unseen categories):

```yaml
schema_name: dw
table_name: fct_orders
column_name: payment_method
detector_slug: zscore_outlier_fraction
params:
  target: new_category_count
  threshold_z: 0.1
baseline:
  window_days: 7
  min_rows: 1000
schedule: "*/30 * * * *"
fail_threshold: 0.0
```

## Expected output

Normal:

```
fct_orders.payment_method  psi                    PASS  PSI=0.02
fct_orders.payment_method  prepaid_card_fraction  PASS  0.031  z=0.4
fct_orders.payment_method  new_category_count     PASS  0 new categories
```

During fraud wave:

```
fct_orders.payment_method  psi                    FAIL  PSI=0.31
fct_orders.payment_method  prepaid_card_fraction  FAIL  0.19  z=5.8  (baseline=0.03)
```

## Why this approach

PSI at 30-minute intervals is the right cadence for fraud signals - daily monitoring
would be too slow. The prepaid card fraction companion gives a single actionable
number rather than requiring the fraud analyst to interpret a full distribution shift.
New category detection catches payment methods that your fraud rules have never seen
(common when testing stolen card BINs of a new type). Baseline of 14 days is long
enough to smooth weekend patterns without hiding an attack that started this week.

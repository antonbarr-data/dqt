# Recipe 01: Monitor SCD Type 2 for unexpected updates

## Problem

SCD Type 2 tables accumulate versioned rows over time. A pipeline bug can silently
close active records, reopen expired ones, or duplicate current-version rows. By the
time downstream reports surface the error, weeks of data may be affected. You need
a check that fires within one run cycle - before the incident spreads.

## dqt check

```yaml
schema_name: dw
table_name: dim_customers
column_name: is_current
detector_slug: zscore_outlier_fraction
params:
  threshold_z: 3.5
baseline:
  window_days: 30
  min_rows: 1000
schedule: "0 * * * *"
scope:
  mode: entire
```

Secondary check for duplicate active keys:

```yaml
schema_name: dw
table_name: dim_customers
column_name: customer_key
detector_slug: ks_pvalue
params:
  alternative: two-sided
filters:
  - col: is_current
    values: [true]
baseline:
  window_days: 30
schedule: "0 * * * *"
```

## Expected output

CLI:

```
dim_customers.is_current  zscore_outlier_fraction  PASS   z=0.42  (baseline p=0.892)
dim_customers.customer_key  ks_pvalue              PASS   p=0.71
```

On a broken SCD load (e.g. all records set `is_current=false`):

```
dim_customers.is_current  zscore_outlier_fraction  FAIL   z=12.4  fraction=0.00 (baseline=0.08)
```

Dashboard shows the `is_current` distribution histogram overlaid against baseline with
the KS supremum point marked.

## Why this approach

The fraction of `is_current=true` rows in a mature SCD table is stable month over
month. A modified Z-score on that fraction detects sudden drops (bulk expire) or
spikes (duplicate inserts) without needing any application-layer knowledge. KS on the
key distribution catches subtle duplicates that don't shift the fraction noticeably.
Raw Z-score would be unreliable here because the fraction can sit near 0 or 1,
making the distribution non-normal - modified Z-score via MAD handles that correctly.

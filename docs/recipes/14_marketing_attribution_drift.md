# Recipe 14: Monitor channel attribution distribution stability

## Problem

Marketing attribution models produce a distribution of credit across channels
(paid search, organic, email, referral, etc.). Attribution drift - caused by UTM
parameter changes, tracking pixel failures, or model updates - looks identical to
a real channel performance shift in the dashboards. You need to separate "the data
changed" from "the business changed."

## dqt check

Wasserstein-1 on the attribution distribution:

```yaml
schema_name: analytics
table_name: fct_attribution
column_name: attribution_channel
detector_slug: psi
params:
  n_bins: 20
baseline:
  window_days: 28
  min_rows: 3000
schedule: "0 7 * * *"
warn_threshold: 0.10
fail_threshold: 0.25
```

Monitor the `(none)` / unattributed fraction:

```yaml
schema_name: analytics
table_name: fct_attribution
column_name: attribution_channel
detector_slug: zscore_outlier_fraction
params:
  target: category_fraction
  category: "(none)"
  threshold_z: 3.5
baseline:
  window_days: 28
  min_rows: 3000
schedule: "0 7 * * *"
fail_threshold: 0.30
warn_threshold: 0.20
```

Track attribution model confidence score distribution for model drift:

```yaml
schema_name: analytics
table_name: fct_attribution
column_name: attribution_confidence
detector_slug: ks_pvalue
params:
  alternative: two-sided
baseline:
  window_days: 28
  min_rows: 3000
schedule: "0 7 * * *"
warn_threshold: 0.05
fail_threshold: 0.001
```

## Expected output

```
fct_attribution.attribution_channel    psi              PASS  PSI=0.04
fct_attribution.attribution_channel    none_fraction    WARN  0.28  z=3.1  (baseline=0.18)
fct_attribution.attribution_confidence ks_pvalue        PASS  p=0.22
```

The WARN on `(none)` fraction with stable KS on confidence scores suggests a UTM
parameter was dropped from a campaign rather than a model regression.

## Why this approach

A rising `(none)` fraction is the most reliable proxy for tracking breakage - it
accumulates unattributable sessions. PSI on the full channel distribution catches
channel mix shifts independent of unattributed volume. Monitoring confidence score
distribution separately isolates model drift from data drift. The combination of
three signals lets you distinguish: (1) tracking broke, (2) channel mix genuinely
shifted, (3) attribution model behavior changed.

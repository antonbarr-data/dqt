# Recipe 02: Detect bot traffic via session length and request rate distribution

## Problem

Bot floods show up as spikes in request volume and collapses in session duration.
Standard threshold alerts miss gradual bot ramp-ups. You need distribution-level
monitoring on `session_duration_s` and `requests_per_session` to catch both sudden
floods and slow synthetic-traffic leakage before they contaminate conversion metrics.

## dqt check

```yaml
schema_name: analytics
table_name: fct_sessions
column_name: session_duration_s
detector_slug: wasserstein_1
params:
  n_bins: 50
baseline:
  window_days: 14
  min_rows: 10000
schedule: "*/30 * * * *"
scope:
  mode: incremental
  key_col: session_started_at
  since: "now() - interval '2 hours'"
warn_threshold: 0.05
fail_threshold: 0.15
```

```yaml
schema_name: analytics
table_name: fct_sessions
column_name: requests_per_session
detector_slug: ks_pvalue
params:
  alternative: two-sided
baseline:
  window_days: 14
  min_rows: 10000
schedule: "*/30 * * * *"
scope:
  mode: incremental
  key_col: session_started_at
  since: "now() - interval '2 hours'"
warn_threshold: 0.05
fail_threshold: 0.001
```

## Expected output

Normal traffic window:

```
fct_sessions.session_duration_s    wasserstein_1  PASS   W=0.032
fct_sessions.requests_per_session  ks_pvalue      PASS   p=0.41
```

During bot flood:

```
fct_sessions.session_duration_s    wasserstein_1  FAIL   W=0.31  (threshold=0.15)
fct_sessions.requests_per_session  ks_pvalue      FAIL   p=0.000003
```

Dashboard renders overlapping CDFs with KS supremum marked and the Wasserstein
transport distance annotated on the chart.

## Why this approach

Session duration under bot traffic typically collapses to a near-zero spike (bots
complete sessions in milliseconds) while request rate spikes. Wasserstein-1 is the
right metric here because it is sensitive to the full shape of the shift, not just
location - it will catch a bimodal distribution where bots coexist with real traffic.
KS on requests-per-session catches the complementary spike. Using both guards
against false positives from legitimate traffic changes like mobile app releases.

# Recipe 10: Ensure control group distributions are stable during an A/B test

## Problem

A/B tests are invalidated when the control group drifts during the experiment window.
This happens from assignment leakage, platform bugs, or selection bias introduced by
mid-experiment changes. You need automated checks on the control group's key
distributions to detect invalidation before the experiment concludes and results
are acted on.

## dqt check

Monitor session duration distribution in the control group:

```yaml
schema_name: analytics
table_name: fct_experiment_assignments
column_name: session_duration_s
detector_slug: ks_pvalue
params:
  alternative: two-sided
baseline:
  window_days: 7
  min_rows: 2000
schedule: "0 * * * *"
filters:
  - col: experiment_id
    values: [exp_checkout_v2]
  - col: variant
    values: [control]
warn_threshold: 0.05
fail_threshold: 0.01
```

Monitor assignment balance (control:treatment ratio):

```yaml
schema_name: analytics
table_name: fct_experiment_assignments
column_name: variant
detector_slug: psi
params:
  n_bins: 2
baseline:
  window_days: 3
  min_rows: 500
schedule: "0 * * * *"
filters:
  - col: experiment_id
    values: [exp_checkout_v2]
warn_threshold: 0.10
fail_threshold: 0.25
```

## Expected output

Stable experiment:

```
fct_experiment_assignments.session_duration_s [control]  ks_pvalue  PASS  p=0.34
fct_experiment_assignments.variant                        psi        PASS  PSI=0.02
```

With control group leakage (treatment users in control bucket):

```
fct_experiment_assignments.session_duration_s [control]  ks_pvalue  FAIL  p=0.0004
fct_experiment_assignments.variant                        psi        WARN  PSI=0.13
```

## Why this approach

KS on the control group's behavior metrics detects distribution drift that mean-only
comparisons would miss. PSI on the variant column detects imbalanced assignment -
the ratio of control to treatment should remain near the configured split. Both checks
run hourly so an assignment bug is caught the same day it's introduced, not after the
experiment runs for 2 weeks. A FAIL on either check should trigger an experiment pause
review, not an automatic stop - that's an HITL decision.

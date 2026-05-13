# Recipe 05: Convert GX ExpectationSuite to dqt checks

## Problem

You have an existing Great Expectations suite with dozens of expectations and want to
migrate to dqt without rewriting everything from scratch. The `dqt.compat.gx`
compatibility shim runs the migration automatically, preserving all threshold values
and adding statistical baselines where GX had only static bounds.

## dqt check

First, export your GX suite to JSON:

```bash
great_expectations suite list
great_expectations suite show my_orders_suite --no-jupyter > my_orders_suite.json
```

Then convert:

```bash
dqt compat gx convert my_orders_suite.json \
  --source postgres://warehouse/dw \
  --output checks/orders/
```

The CLI writes one YAML file per expectation. Example of what a converted check looks
like for `expect_column_values_to_not_be_null`:

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_id
detector_slug: zscore_outlier_fraction
params:
  target: null_fraction
  threshold_z: 3.5
baseline:
  window_days: 14
  min_rows: 1000
schedule: "0 6 * * *"
fail_threshold: 0.001
```

And for `expect_column_values_to_be_between` on a numeric column:

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_revenue_usd
detector_slug: adjusted_boxplot_fraction
params:
  fence_multiplier: 1.5
baseline:
  window_days: 14
  min_rows: 1000
schedule: "0 6 * * *"
```

## Expected output

```
Converting my_orders_suite.json (34 expectations)...
  converted:  31
  skipped:     2  (expect_column_pair_values_to_be_equal - no direct equivalent)
  upgraded:    1  (expect_column_mean_to_be_between -> wasserstein_1 recommended)

Output written to checks/orders/ (31 files)
Review skipped items: checks/orders/_migration_report.txt
```

## Why this approach

GX static bounds (`min_value`, `max_value`) are brittle - they need manual updates
every time the business changes. dqt replaces them with baseline-fitted statistical
checks that adapt automatically. The compat shim uses adjusted boxplot instead of
raw IQR for the range checks because it handles skewed distributions (revenue, counts)
without inflating false positives. The two skipped expectations have no direct
statistical equivalent and are flagged for manual review rather than silently dropped.

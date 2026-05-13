# Recipe 03: Monitor revenue per segment for drift using Wasserstein-1

## Problem

Revenue distribution across customer segments shifts when a pricing change, promotion,
or data pipeline error affects one segment disproportionately. Aggregate-level metrics
(total revenue, mean order value) often stay flat while the underlying mix changes,
hiding the issue until a segment-level report is pulled manually.

## dqt check

```yaml
schema_name: dw
table_name: fct_orders
column_name: order_revenue_usd
detector_slug: wasserstein_1
params:
  n_bins: 100
baseline:
  window_days: 28
  min_rows: 5000
schedule: "0 6 * * *"
filters:
  - col: customer_segment
    values: [enterprise]
warn_threshold: 0.08
fail_threshold: 0.20
```

Repeat for each segment (`smb`, `consumer`, `trial`) with the same config.
Use a YAML anchor to avoid duplication:

```yaml
# _base: &base
#   detector_slug: wasserstein_1
#   params: {n_bins: 100}
#   baseline: {window_days: 28, min_rows: 5000}
#   schedule: "0 6 * * *"
#   warn_threshold: 0.08
#   fail_threshold: 0.20
#   schema_name: dw
#   table_name: fct_orders
#   column_name: order_revenue_usd

schema_name: dw
table_name: fct_orders
column_name: order_revenue_usd
detector_slug: wasserstein_1
params:
  n_bins: 100
baseline:
  window_days: 28
  min_rows: 5000
schedule: "0 6 * * *"
filters:
  - col: customer_segment
    values: [smb]
warn_threshold: 0.08
fail_threshold: 0.20
```

## Expected output

```
fct_orders.order_revenue_usd [enterprise]  wasserstein_1  PASS  W=0.041
fct_orders.order_revenue_usd [smb]         wasserstein_1  WARN  W=0.11  (threshold=0.08)
fct_orders.order_revenue_usd [consumer]    wasserstein_1  PASS  W=0.029
fct_orders.order_revenue_usd [trial]       wasserstein_1  PASS  W=0.055
```

Dashboard: `HistDual` chart shows current vs baseline revenue histogram for SMB
segment, with the Wasserstein distance labeled on the transport path.

## Why this approach

Wasserstein-1 (earth-mover distance) measures the minimum cost to transform one
distribution into another. It is sensitive to both location shifts (mean revenue
moved) and shape changes (revenue became more bimodal due to a promo). PSI is an
alternative but requires fixed bin boundaries; Wasserstein-1 is boundary-free.
KL divergence would be unstable if any bin has near-zero density, which is common
in revenue distributions with long tails. Use `n_bins: 100` to capture tail detail
on revenue data.

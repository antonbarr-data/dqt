---
type: column
dataset: gig_vendor_stats
name: n_active_vendors
classification: internal
pii: false
tags:
---
# n_active_vendors

> Dataset: [[raw/datasets/gig_vendor_stats]]

Count of sellers with at least one active gig listing in this category. Values â‰¤0 indicate a data pipeline error. Higher counts suppress avg_price_usd with a 1-week lag (competition effect).

## Metadata

| Field | Value |
|---|---|
| Classification | internal |
| PII | No |
| Unit | — |

## Upstream Lineage

_No upstream lineage_

## Downstream Lineage

- [[raw/columns/gig_prices/avg_price_usd]] → causality (lag 1w, r=0.55)
- [[raw/datasets/weekly_vendor_count]] → aggregates

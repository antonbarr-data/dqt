---
type: column
dataset: gig_prices
name: avg_price_usd
classification: internal
pii: false
tags:
---
# avg_price_usd

> Dataset: [[raw/datasets/gig_prices]]

Average listed price in USD across all active gigs in this category on this date. NULL indicates a data collection failure.

## Metadata

| Field | Value |
|---|---|
| Classification | internal |
| PII | No |
| Unit | — |

## Upstream Lineage

- [[raw/columns/gig_vendor_stats/n_active_vendors]] ← causality (lag 1w)

## Downstream Lineage

- [[raw/columns/gigler_transactions/amount_usd]] → causality (lag 1w, r=0.55)
- [[raw/datasets/weekly_avg_gig_price]] → aggregates

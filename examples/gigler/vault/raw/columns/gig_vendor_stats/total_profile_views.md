---
type: column
dataset: gig_vendor_stats
name: total_profile_views
classification: internal
pii: false
tags:
---
# total_profile_views

> Dataset: [[raw/datasets/gig_vendor_stats]]

Total buyer views of seller profiles in this category on this day. NULL indicates a tracking pixel outage. Strong predictor of transaction volume with a 1-week lag (eyeball-to-purchase funnel).

## Metadata

| Field | Value |
|---|---|
| Classification | internal |
| PII | No |
| Unit | — |

## Upstream Lineage

_No upstream lineage_

## Downstream Lineage

- [[raw/columns/gigler_transactions/amount_usd]] → causality (lag 1w, r=0.65)
- [[raw/datasets/weekly_profile_views]] → aggregates

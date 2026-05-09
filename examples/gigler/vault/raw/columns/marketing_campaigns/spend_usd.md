---
type: column
dataset: marketing_campaigns
name: spend_usd
classification: internal
pii: false
tags:
---
# spend_usd

> Dataset: [[raw/datasets/marketing_campaigns]]

Total campaign spend in USD for this day. Spikes >$5,000/day may indicate budget misconfiguration.

## Metadata

| Field | Value |
|---|---|
| Classification | internal |
| PII | No |
| Unit | — |

## Upstream Lineage

_No upstream lineage_

## Downstream Lineage

- [[raw/columns/gigler_transactions/amount_usd]] → causality (lag 2w, r=0.60)
- [[raw/datasets/weekly_acquisition_spend]] → aggregates

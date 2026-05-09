---
type: column
dataset: gigler_transactions
name: amount_usd
classification: internal
pii: false
tags:
---
# amount_usd

> Dataset: [[raw/datasets/gigler_transactions]]

Gross transaction value in USD. Values >$5,000 indicate enterprise/custom contracts. Values <$1 indicate data entry errors.

## Metadata

| Field | Value |
|---|---|
| Classification | internal |
| PII | No |
| Unit | — |

## Upstream Lineage

- [[raw/columns/marketing_campaigns/spend_usd]] ← causality (lag 2w)

## Downstream Lineage

- [[raw/datasets/weekly_transaction_volume]] → aggregates
- [[raw/columns/gigler_transactions/platform_fee_usd]] → derived_from

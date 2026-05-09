---
type: column
dataset: gigler_transactions
name: amount_usd
classification: internal
pii: false
tags:
---
# amount_usd

> Dataset: [[Datasets/gigler_transactions]]

Gross transaction value in USD. Values >$5,000 indicate enterprise/custom contracts. Values <$1 indicate data entry errors.

## Metadata

| Field | Value |
|---|---|
| Classification | internal |
| PII | No |
| Unit | — |

## Upstream Lineage

- [[Columns/marketing_campaigns/spend_usd]] <- causality (lag 2w)

## Downstream Lineage

- [[Datasets/weekly_transaction_volume]] -> aggregates
- [[Columns/gigler_transactions/platform_fee_usd]] -> derived_from

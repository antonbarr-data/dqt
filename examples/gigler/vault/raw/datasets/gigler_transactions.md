---
type: dataset
id: gigler_transactions
domain: platform
owner: platform-analytics@gigler.com
freshness_sla_hours: 4.0
classification: internal
tags:
  - platform
---
# gigler_transactions

Transaction records from the Gigler freelance marketplace platform. Each row represents one completed, cancelled, or disputed transaction.

## Metadata

| Field | Value |
|---|---|
| Owner | platform-analytics@gigler.com |
| Domain | platform |
| Freshness SLA | 4.0h |
| Columns | 16 |

## Columns

- [[raw/columns/gigler_transactions/transaction_id|transaction_id]] — Unique transaction identifier. Format: TXN-NNNNNN.
- [[raw/columns/gigler_transactions/date|date]] — Date of transaction creation. ISO 8601.
- [[raw/columns/gigler_transactions/gig_category|gig_category]] — Service category of the gig purchased.
- [[raw/columns/gigler_transactions/seller_country|seller_country]] — Country of the freelance seller.
- [[raw/columns/gigler_transactions/buyer_country|buyer_country]] — Country of the buyer/client.
- [[raw/columns/gigler_transactions/seller_profession|seller_profession]] — Self-reported profession of the seller.
- [[raw/columns/gigler_transactions/amount_usd|amount_usd]] — Gross transaction value in USD. Values >$5,000 indicate ente
- [[raw/columns/gigler_transactions/currency|currency]] — Original transaction currency before USD conversion.
- [[raw/columns/gigler_transactions/payment_method|payment_method]] — Payment method used. Enum: credit_card, paypal, bank_transfe
- [[raw/columns/gigler_transactions/status|status]] — Transaction lifecycle status. completed=delivered, cancelled
- [[raw/columns/gigler_transactions/completion_days|completion_days]] — Calendar days from order to delivery. Values >30 indicate si
- [[raw/columns/gigler_transactions/rating|rating]] — Buyer satisfaction rating 1.0-5.0. NULL if transaction not y
- [[raw/columns/gigler_transactions/is_repeat_buyer|is_repeat_buyer]] — True if the buyer has transacted on Gigler before.
- [[raw/columns/gigler_transactions/platform_fee_usd|platform_fee_usd]] — Gigler platform commission (20% of amount_usd).
- [[raw/columns/gigler_transactions/seller_level|seller_level]] — Freelancer tier: new_seller, rising_talent, level_1, level_2
- [[raw/columns/gigler_transactions/week_number|week_number]] — ISO week number for time-series aggregation.

## Relationships

_None_

---
type: dataset
id: gig_prices
domain: marketplace
owner: marketplace-analytics@gigler.com
freshness_sla_hours: 24.0
classification: internal
tags:
  - marketplace
---
# gig_prices

Daily snapshot of gig listing prices per category on the Gigler marketplace. Lower prices correlate with increased buyer interest and transaction volume with a 1-week lag.

## Metadata

| Field | Value |
|---|---|
| Owner | marketplace-analytics@gigler.com |
| Domain | marketplace |
| Freshness SLA | 24.0h |
| Columns | 9 |

## Columns

- [[raw/columns/gig_prices/date|date]] — Snapshot date. ISO 8601.
- [[raw/columns/gig_prices/gig_category|gig_category]] — Gig service category. Matches gig_category in gigler_transac
- [[raw/columns/gig_prices/avg_price_usd|avg_price_usd]] — Average listed price in USD across all active gigs in this c
- [[raw/columns/gig_prices/median_price_usd|median_price_usd]] — Median listed price in USD. More robust to outlier listings 
- [[raw/columns/gig_prices/min_price_usd|min_price_usd]] — Lowest active listing price in USD. Values below $5 indicate
- [[raw/columns/gig_prices/max_price_usd|max_price_usd]] — Highest active listing price in USD. Values above $50,000 in
- [[raw/columns/gig_prices/n_listings|n_listings]] — Number of active gig listings in this category on this date.
- [[raw/columns/gig_prices/discount_active|discount_active]] — True when a platform-wide promotional discount is active (e.
- [[raw/columns/gig_prices/price_change_pct|price_change_pct]] — Week-over-week percentage change in avg_price_usd for this c

## Relationships

_None_

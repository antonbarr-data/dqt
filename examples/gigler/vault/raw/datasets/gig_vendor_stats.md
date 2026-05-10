---
type: dataset
id: gig_vendor_stats
domain: marketplace
owner: marketplace-analytics@gigler.com
freshness_sla_hours: 24.0
classification: internal
tags:
  - marketplace
---
# gig_vendor_stats

Daily snapshot of vendor competition metrics per gig category on the Gigler marketplace. Captures how many sellers compete in each category, their quality ratings, and buyer engagement (profile views, search impressions). Higher vendor counts suppress prices with a 1-week lag; higher profile views predict transaction volume with a 1-week lag.

## Metadata

| Field | Value |
|---|---|
| Owner | marketplace-analytics@gigler.com |
| Domain | marketplace |
| Freshness SLA | 24.0h |
| Columns | 11 |

## Columns

- [[raw/columns/gig_vendor_stats/date|date]] — Snapshot date. ISO 8601.
- [[raw/columns/gig_vendor_stats/gig_category|gig_category]] — Gig service category. Matches gig_category in gig_prices and
- [[raw/columns/gig_vendor_stats/n_active_vendors|n_active_vendors]] — Count of sellers with at least one active gig listing in thi
- [[raw/columns/gig_vendor_stats/n_new_vendors|n_new_vendors]] — Vendors who published their first listing in this category i
- [[raw/columns/gig_vendor_stats/avg_vendor_rating|avg_vendor_rating]] — Platform-wide average buyer rating (1.0-5.0) for all sellers
- [[raw/columns/gig_vendor_stats/top_rated_fraction|top_rated_fraction]] — Fraction of sellers in this category with level_2 or top_rat
- [[raw/columns/gig_vendor_stats/total_profile_views|total_profile_views]] — Total buyer views of seller profiles in this category on thi
- [[raw/columns/gig_vendor_stats/avg_profile_views|avg_profile_views]] — total_profile_views / n_active_vendors. Measures demand inte
- [[raw/columns/gig_vendor_stats/search_impressions|search_impressions]] — Number of times gigs in this category appeared in buyer sear
- [[raw/columns/gig_vendor_stats/click_through_rate|click_through_rate]] — Ratio of profile clicks to search impressions (0.0-1.0). Val
- [[raw/columns/gig_vendor_stats/avg_response_time_hours|avg_response_time_hours]] — Average hours for a seller in this category to respond to bu

## Relationships

_None_

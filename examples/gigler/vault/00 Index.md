# Gigler Knowledge Graph

This vault documents data assets, column semantics, and discovered relationships.

## Structure

| Folder | Contents |
|---|---|
| `raw/datasets/` | Source-of-truth dataset descriptions (semantic layer) |
| `raw/columns/` | Per-column atomic notes with metadata and lineage links |
| `wiki/metrics/` | Derived metrics and aggregations |
| `wiki/lineage/` | Discovered causal and lineage relationships |

## Datasets

- [[raw/datasets/marketing_campaigns|marketing_campaigns]] — marketing
- [[raw/datasets/gigler_transactions|gigler_transactions]] — platform
- [[raw/datasets/gig_prices|gig_prices]] — marketplace
- [[raw/datasets/gig_vendor_stats|gig_vendor_stats]] — marketplace

## Metrics

- [[wiki/metrics/weekly_acquisition_spend|Weekly Acquisition Spend]]
- [[wiki/metrics/weekly_transaction_volume|Weekly Transaction Volume]]
- [[wiki/metrics/weekly_avg_gig_price|Weekly Avg Gig Price]]
- [[wiki/metrics/weekly_vendor_count|Weekly Active Vendor Count]]
- [[wiki/metrics/weekly_profile_views|Weekly Profile Views]]

## Lineage
- [[wiki/lineage/causality]] — Causal relationships between datasets

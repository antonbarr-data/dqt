# Causal Relationships

Directed causal edges discovered by statistical analysis (Granger causality / lag-correlation).

| Source | Target | Lag | Confidence | Description |
|---|---|---|---|---|
| [[raw/columns/marketing_campaigns/spend_usd\|marketing_campaigns.spend_usd]] | [[raw/columns/gigler_transactions/amount_usd\|gigler_transactions.amount_usd]] | 2w | 0.60 | Acquisition spend drives transaction volume with 2-week lag (Pearson r=0.603) |
| [[raw/columns/gig_prices/avg_price_usd\|gig_prices.avg_price_usd]] | [[raw/columns/gigler_transactions/amount_usd\|gigler_transactions.amount_usd]] | 1w | 0.55 | Lower avg gig price drives higher transaction volume with 1-week lag (Pearson r≈-0.55, negative direction) |
| [[raw/columns/gig_vendor_stats/n_active_vendors\|gig_vendor_stats.n_active_vendors]] | [[raw/columns/gig_prices/avg_price_usd\|gig_prices.avg_price_usd]] | 1w | 0.55 | More competing vendors suppress avg gig price with 1-week lag (Pearson r≈-0.55, competition effect) |
| [[raw/columns/gig_vendor_stats/total_profile_views\|gig_vendor_stats.total_profile_views]] | [[raw/columns/gigler_transactions/amount_usd\|gigler_transactions.amount_usd]] | 1w | 0.65 | Higher buyer profile views drive transaction volume with 1-week lag (Pearson r≈+0.65, eyeball-to-purchase funnel) |

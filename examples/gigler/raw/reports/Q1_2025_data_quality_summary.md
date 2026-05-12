# Q1 2025 Data Quality Summary — Gigler Platform

**Period:** 2025-01-01 – 2025-03-31  
**Prepared by:** platform-data@gigler.io  
**Review date:** 2025-04-07

## Executive Summary

Q1 2025 saw 3 P1 incidents and 11 P2 incidents across the Gigler data platform,
down from 5 P1 and 14 P2 in Q4 2024. Mean time to detect (MTTD) improved from 4.2h
to 2.1h, driven by the deployment of STL anomaly detection on all 4 core datasets.

## Dataset Health Scorecard

| Dataset | Checks | Pass | Warn | Fail | MTTD |
|---|---|---|---|---|---|
| marketing_campaigns | 18 | 16 | 1 | 1 | 1.8h |
| gigler_transactions | 24 | 22 | 2 | 0 | 2.3h |
| gig_prices | 12 | 11 | 1 | 0 | 1.5h |
| gig_vendor_stats | 16 | 15 | 0 | 1 | 2.6h |

## Notable Incidents

### INC-2025-004: marketing_campaigns null spike (P1, Jan 14)
campaign_id column had 12% nulls for 3 days due to upstream ETL schema change.
Resolved by adding NOT NULL constraint + alerting on null_fraction > 2%.

### INC-2025-017: gig_vendor_stats freshness breach (P2, Feb 22)
avg_vendor_rating not updated for 31h (SLA: 24h). Root cause: Airflow task
dependency misconfiguration after infra migration.

## Recommendations

1. **Increase baseline refit cadence** for gig_prices from monthly to weekly —
   seasonal price effects are causing stale baselines in holiday weeks.
2. **Add schema change alerting** to marketing_campaigns ETL.
3. **Enable BOCPD changepoint detection** on gigler_transactions.amount_usd —
   manual review identified 2 undetected changepoints in Q1.

## Coverage Metrics

- 70 out of 82 key columns are now watched (85%)
- 4 datasets fully covered, 2 datasets partially covered
- 0 datasets with no coverage (target: 100% by Q2 2025)

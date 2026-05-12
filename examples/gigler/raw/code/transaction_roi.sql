-- Weekly ROI bridge: marketing spend → transaction volume
-- Source tables: marketing_campaigns, gigler_transactions, gig_prices
-- Grain: ISO week × gig_category

WITH weekly_spend AS (
    SELECT
        date_trunc('week', date)::date          AS week_start,
        SUM(spend_usd)                          AS total_spend_usd,
        SUM(conversions)                        AS total_conversions,
        SUM(revenue_usd)                        AS attributed_revenue_usd
    FROM marketing_campaigns
    WHERE quality_score >= 3
    GROUP BY 1
),
weekly_txn AS (
    SELECT
        date_trunc('week', date)::date          AS week_start,
        gig_category,
        COUNT(*)                                AS transaction_count,
        SUM(amount_usd)                         AS gross_volume_usd,
        SUM(platform_fee_usd)                   AS platform_revenue_usd,
        AVG(rating)                             AS avg_rating,
        SUM(is_repeat_buyer::int)               AS repeat_buyers
    FROM gigler_transactions
    WHERE status = 'completed'
    GROUP BY 1, 2
),
weekly_price AS (
    SELECT
        date_trunc('week', date)::date          AS week_start,
        gig_category,
        AVG(avg_price_usd)                      AS avg_price_usd,
        SUM(n_listings)                         AS total_listings
    FROM gig_prices
    GROUP BY 1, 2
)
SELECT
    t.week_start,
    t.gig_category,
    t.transaction_count,
    t.gross_volume_usd,
    t.platform_revenue_usd,
    t.avg_rating,
    t.repeat_buyers,
    p.avg_price_usd,
    p.total_listings,
    s.total_spend_usd,
    s.total_conversions,
    s.attributed_revenue_usd,
    -- ROI: platform revenue vs marketing cost (lagged 2w to match causal lag)
    ROUND(
        (t.platform_revenue_usd - LAG(s.total_spend_usd, 2) OVER (ORDER BY t.week_start))
        / NULLIF(LAG(s.total_spend_usd, 2) OVER (ORDER BY t.week_start), 0),
        4
    ) AS lagged_platform_roi
FROM weekly_txn t
LEFT JOIN weekly_price p USING (week_start, gig_category)
LEFT JOIN weekly_spend s USING (week_start)
ORDER BY t.week_start, t.gig_category;

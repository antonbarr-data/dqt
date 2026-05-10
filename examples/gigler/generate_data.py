#!/usr/bin/env python3
"""
Generate sample data for Gigler + marketing campaigns demo.
Run: python examples/gigler/generate_data.py

Causality chain (all detectable via Granger / lag-correlation):
  - n_active_vendors   → avg_price_usd     (1-week lag, r ≈ -0.55): competition drives prices down
  - Acquisition spend  → transaction volume (2-week lag, r ≈ +0.60)
  - Avg gig price      → transaction volume (1-week lag, r ≈ -0.55)
  - total_profile_views → transaction volume (1-week lag, r ≈ +0.65): eyeballs convert to purchases
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

QUARTERS = [
    ("2024-01-01", "2024-03-31"),
    ("2024-04-01", "2024-06-30"),
    ("2024-07-01", "2024-09-30"),
    ("2024-10-01", "2024-12-31"),
    ("2025-01-01", "2025-03-31"),
]
QUARTER_NAMES = ["2024_q1", "2024_q2", "2024_q3", "2024_q4", "2025_q1"]

GEOS = ["US", "GB", "DE", "FR", "IN", "BR", "CA", "AU", "IL", "SG", "NL", "ES", "MX", "JP", "ZA"]
GEO_WEIGHTS = [0.30, 0.10, 0.07, 0.06, 0.15, 0.05, 0.04, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.02, 0.03]

GEO_CITIES = {
    "US": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "San Francisco", "Seattle"],
    "GB": ["London", "Manchester", "Birmingham", "Glasgow", "Leeds", "Bristol"],
    "DE": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart"],
    "FR": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Bordeaux"],
    "IN": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata"],
    "BR": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza"],
    "CA": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"],
    "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
    "IL": ["Tel Aviv", "Jerusalem", "Haifa", "Beer Sheva", "Netanya"],
    "SG": ["Singapore"],
    "NL": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven"],
    "ES": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao"],
    "MX": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana"],
    "JP": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo"],
    "ZA": ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth"],
}

GEO_LANGUAGE = {
    "US": "English", "GB": "English", "CA": "English", "AU": "English",
    "IN": "Hindi", "DE": "German", "FR": "French",
    "ES": "Spanish", "MX": "Spanish", "BR": "Portuguese",
    "IL": "Hebrew", "NL": "Dutch", "JP": "Japanese",
    "ZA": "Afrikaans", "SG": "English",
}

PROFESSIONS = [
    "Software Engineer", "Designer", "Marketing Manager", "Data Scientist",
    "Product Manager", "Writer", "Accountant", "Consultant", "Teacher",
    "HR Manager", "Sales Rep", "Lawyer", "Physician", "Architect", "Researcher",
]

CHANNELS = ["social_media", "email", "search", "display", "influencer", "content_marketing"]
CHANNEL_WEIGHTS = [0.30, 0.25, 0.20, 0.10, 0.08, 0.07]

# CTR by channel (mean)
CHANNEL_CTR = {
    "search": 0.075, "social_media": 0.020, "display": 0.012,
    "email": 0.030, "influencer": 0.025, "content_marketing": 0.018,
}
# impressions range multiplier by channel
CHANNEL_IMPRESSIONS_SCALE = {
    "search": 1.0, "social_media": 2.5, "display": 3.0,
    "email": 0.5, "influencer": 1.8, "content_marketing": 0.8,
}

CAMPAIGN_TYPES = ["awareness", "acquisition", "retention", "re_engagement"]
CAMPAIGN_TYPE_WEIGHTS = [0.25, 0.40, 0.25, 0.10]

PRICE_RANGES = ["budget", "mid", "premium"]
PRICE_RANGE_WEIGHTS = [0.35, 0.45, 0.20]

# average order value by price_range × profession tier
PROFESSION_TIER = {
    "Lawyer": "high", "Physician": "high", "Data Scientist": "high",
    "Software Engineer": "high", "Architect": "high",
    "Consultant": "mid", "Product Manager": "mid", "Accountant": "mid",
    "Researcher": "mid", "Marketing Manager": "mid",
    "Designer": "low", "Writer": "low", "Teacher": "low",
    "HR Manager": "low", "Sales Rep": "low",
}
AOV_BASE = {"budget": 150, "mid": 800, "premium": 4000}
TIER_MULTIPLIER = {"high": 1.4, "mid": 1.0, "low": 0.7}

GIG_CATEGORIES = [
    "Web Development", "Mobile App", "Graphic Design", "Content Writing",
    "SEO/SEM", "Video Production", "Data Analysis", "AI/ML Development",
    "Translation", "Legal Consulting", "Financial Modeling", "Music Production",
    "Photography", "Social Media Management", "Virtual Assistant",
]

GIG_TO_PROFESSION = {
    "Web Development": "Software Engineer", "Mobile App": "Software Engineer",
    "Graphic Design": "Designer", "Content Writing": "Writer",
    "SEO/SEM": "Marketing Manager", "Video Production": "Designer",
    "Data Analysis": "Data Scientist", "AI/ML Development": "Data Scientist",
    "Translation": "Writer", "Legal Consulting": "Lawyer",
    "Financial Modeling": "Accountant", "Music Production": "Designer",
    "Photography": "Designer", "Social Media Management": "Marketing Manager",
    "Virtual Assistant": "HR Manager",
}

# median completion days per gig category
GIG_COMPLETION_DAYS = {
    "Web Development": 14, "Mobile App": 21, "Graphic Design": 5,
    "Content Writing": 3, "SEO/SEM": 10, "Video Production": 7,
    "Data Analysis": 7, "AI/ML Development": 18, "Translation": 3,
    "Legal Consulting": 14, "Financial Modeling": 10, "Music Production": 12,
    "Photography": 4, "Social Media Management": 7, "Virtual Assistant": 2,
}

SELLER_LEVELS = ["new_seller", "rising_talent", "level_1", "level_2", "top_rated"]
SELLER_LEVEL_WEIGHTS = [0.15, 0.20, 0.30, 0.25, 0.10]

PAYMENT_METHODS = ["credit_card", "paypal", "bank_transfer", "crypto"]
PAYMENT_WEIGHTS = [0.50, 0.30, 0.15, 0.05]

TRANSACTION_STATUSES = ["completed", "cancelled", "disputed", "in_progress"]
STATUS_WEIGHTS = [0.950, 0.030, 0.015, 0.005]

CURRENCIES = ["USD", "EUR", "GBP", "ILS", "INR"]
CURRENCY_WEIGHTS = [0.75, 0.10, 0.08, 0.04, 0.03]

# ---- Gig Prices -------------------------------------------------------
# Base median price per category (USD). These are realistic Fiverr/Upwork benchmarks.
GIG_PRICE_BASE = {
    "Web Development":         450,
    "Mobile App":              600,
    "Graphic Design":          120,
    "Content Writing":          60,
    "SEO/SEM":                 250,
    "Video Production":        300,
    "Data Analysis":           350,
    "AI/ML Development":       700,
    "Translation":              80,
    "Legal Consulting":        800,
    "Financial Modeling":      500,
    "Music Production":        200,
    "Photography":             150,
    "Social Media Management": 180,
    "Virtual Assistant":        50,
}

# Typical active listing counts per category
N_LISTINGS_BASE = {
    "Web Development":         4500, "Mobile App":              2800,
    "Graphic Design":          6200, "Content Writing":         8100,
    "SEO/SEM":                 3200, "Video Production":        2100,
    "Data Analysis":           3700, "AI/ML Development":       2400,
    "Translation":             5200, "Legal Consulting":         900,
    "Financial Modeling":      1200, "Music Production":        1800,
    "Photography":             2600, "Social Media Management": 4100,
    "Virtual Assistant":       5800,
}

# Promotional discount periods: (start, end, label, discount_fraction)
SALE_PERIODS = [
    ("2024-04-15", "2024-05-15", "spring_sale",   0.22),  # Gigler Spring Sale
    ("2024-11-20", "2024-12-05", "black_friday",  0.28),  # Black Friday / Cyber Monday
]

# Base active vendor counts per category (sellers with ≥1 active listing)
# Consistent with N_LISTINGS_BASE: avg ~1.4 listings per vendor
N_VENDORS_BASE = {
    "Web Development":         3200,
    "Mobile App":              1900,
    "Graphic Design":          4800,
    "Content Writing":         6500,
    "SEO/SEM":                 2100,
    "Video Production":        1400,
    "Data Analysis":           2600,
    "AI/ML Development":       1700,
    "Translation":             3800,
    "Legal Consulting":         600,
    "Financial Modeling":       850,
    "Music Production":        1200,
    "Photography":             1800,
    "Social Media Management": 3000,
    "Virtual Assistant":       4200,
}

# Platform-wide average vendor rating per category (higher for specialist categories)
CATEGORY_RATING_BASE = {
    "Legal Consulting":        4.6,
    "Financial Modeling":      4.5,
    "AI/ML Development":       4.4,
    "Data Analysis":           4.3,
    "Web Development":         4.3,
    "Mobile App":              4.2,
    "Video Production":        4.2,
    "Photography":             4.1,
    "Graphic Design":          4.1,
    "Content Writing":         4.0,
    "SEO/SEM":                 4.0,
    "Music Production":        3.9,
    "Translation":             3.9,
    "Social Media Management": 3.8,
    "Virtual Assistant":       3.8,
}


def _rng_for(seed_offset: int) -> np.random.Generator:
    return np.random.default_rng(42 + seed_offset * 97)


def generate_vendor_competition(
    quarter_start: str,
    quarter_end: str,
    seed_offset: int,
) -> pd.DataFrame:
    """Daily snapshot of vendor competition metrics per gig category.

    Causal signals baked in:
    - n_active_vendors ↑ → avg_price_usd ↓ (1-week lag): competition suppresses prices
    - total_profile_views ↑ → transaction_count ↑ (1-week lag): eyeballs convert to purchases
    DQ: 0.3% NULL search_impressions, 0.2% NULL total_profile_views,
    0.4% invalid n_active_vendors (≤0), 0.3% click_through_rate > 1.0.
    """
    rng = _rng_for(seed_offset)
    dates = pd.date_range(quarter_start, quarter_end)
    sale_ranges = [(pd.Timestamp(s), pd.Timestamp(e)) for s, e, _, _ in SALE_PERIODS]

    rows = []
    for date in dates:
        days_since_epoch = (date - pd.Timestamp("2024-01-01")).days
        trend = 1.0 + 0.00022 * days_since_epoch  # ~8% annual vendor market growth

        month = date.month
        if month in (3, 4, 5, 6):
            seasonal_vendors = 1.12
            seasonal_views = 1.05   # spring: slightly above average
        elif month in (7, 8, 9):
            seasonal_vendors = 0.95
            seasonal_views = 0.78   # summer: well below average
        elif month in (10, 11, 12):
            seasonal_vendors = 1.05
            seasonal_views = 1.38   # Q4: peak browsing aligns with holiday buying
        else:
            seasonal_vendors = 0.98
            seasonal_views = 0.88   # Q1: post-holiday slump, below average

        # Professionals browse more on weekdays
        dow = date.dayofweek  # 0=Mon, 6=Sun
        if dow < 3:
            dow_views = 1.20
        elif dow < 5:
            dow_views = 1.00
        elif dow == 5:
            dow_views = 0.70
        else:
            dow_views = 0.65

        is_sale = any(s <= date <= e for s, e in sale_ranges)
        sale_views_mult = 1.50 if is_sale else 1.0

        for cat in GIG_CATEGORIES:
            base = N_VENDORS_BASE[cat]
            n_vendors = max(
                10,
                int(base * trend * seasonal_vendors * rng.uniform(0.88, 1.12)),
            )
            n_new = max(0, int(rng.lognormal(np.log(max(1, int(n_vendors * 0.007))), 0.5)))

            base_rating = CATEGORY_RATING_BASE[cat]
            avg_rating = float(np.clip(
                base_rating
                + 0.00010 * days_since_epoch
                - (0.05 if month in (7, 8) else 0.0)
                + rng.normal(0, 0.06),
                1.0, 5.0,
            ))
            top_rated_frac = float(np.clip(rng.normal(0.15, 0.03), 0.05, 0.40))

            # Better-rated vendors attract more profile views per head
            views_per_vendor = (
                4.5
                * (avg_rating / 4.2)
                * seasonal_views
                * dow_views
                * sale_views_mult
                * rng.uniform(0.80, 1.20)
            )
            total_views = max(0, int(n_vendors * views_per_vendor))
            avg_views = round(total_views / max(1, n_vendors), 1)

            search_impr = max(0, int(total_views * rng.uniform(12, 18)))
            ctr = float(np.clip(rng.normal(0.045, 0.008), 0.01, 0.15))
            resp_hours = float(np.clip(rng.lognormal(np.log(8.0), 0.70), 0.5, 72.0))

            rows.append({
                "date":                    date.strftime("%Y-%m-%d"),
                "gig_category":            cat,
                "n_active_vendors":        n_vendors,
                "n_new_vendors":           n_new,
                "avg_vendor_rating":       round(avg_rating, 2),
                "top_rated_fraction":      round(top_rated_frac, 3),
                "total_profile_views":     total_views,
                "avg_profile_views":       avg_views,
                "search_impressions":      search_impr,
                "click_through_rate":      round(ctr, 4),
                "avg_response_time_hours": round(resp_hours, 1),
            })

    df = pd.DataFrame(rows)

    # DQ injections
    n_null_srch = max(1, int(len(df) * 0.003))
    df.loc[rng.choice(len(df), n_null_srch, replace=False), "search_impressions"] = np.nan

    n_null_views = max(1, int(len(df) * 0.002))
    df.loc[rng.choice(len(df), n_null_views, replace=False), "total_profile_views"] = np.nan

    n_bad_vendors = max(1, int(len(df) * 0.004))
    df.loc[rng.choice(len(df), n_bad_vendors, replace=False), "n_active_vendors"] = (
        rng.integers(-5, 1, n_bad_vendors)
    )

    n_bad_ctr = max(1, int(len(df) * 0.003))
    df.loc[rng.choice(len(df), n_bad_ctr, replace=False), "click_through_rate"] = (
        rng.uniform(1.01, 2.50, n_bad_ctr).round(4)
    )

    return df.sort_values(["date", "gig_category"]).reset_index(drop=True)


def _build_weekly_profile_views(vendor_df: pd.DataFrame) -> pd.Series:
    """Weekly total profile views (all categories), indexed by ISO week 'YYYY-WW'."""
    views = vendor_df.dropna(subset=["total_profile_views"]).copy()
    views["date"] = pd.to_datetime(views["date"])
    views["iso_week"] = views["date"].dt.strftime("%G-%V")
    return views.groupby("iso_week")["total_profile_views"].sum()


def generate_marketing_campaigns(
    quarter_start: str,
    quarter_end: str,
    n_rows: int,
    seed_offset: int,
    inject_q3_outage: bool = False,
) -> pd.DataFrame:
    rng = _rng_for(seed_offset)
    qstart = pd.Timestamp(quarter_start)
    qend = pd.Timestamp(quarter_end)
    n_days = (qend - qstart).days + 1

    # distribute rows across days (roughly uniform, slight weekday bias)
    dates = pd.date_range(qstart, qend)
    day_weights = np.array([1.2 if d.weekday() < 5 else 0.6 for d in dates], dtype=float)
    day_weights /= day_weights.sum()
    row_dates = rng.choice(dates, size=n_rows, p=day_weights)

    geos = rng.choice(GEOS, size=n_rows, p=GEO_WEIGHTS)
    cities = [rng.choice(GEO_CITIES[g]) for g in geos]
    languages = [GEO_LANGUAGE[g] for g in geos]
    professions = rng.choice(PROFESSIONS, size=n_rows)
    price_ranges = rng.choice(PRICE_RANGES, size=n_rows, p=PRICE_RANGE_WEIGHTS)
    channels = rng.choice(CHANNELS, size=n_rows, p=CHANNEL_WEIGHTS)
    campaign_types = rng.choice(CAMPAIGN_TYPES, size=n_rows, p=CAMPAIGN_TYPE_WEIGHTS)

    # impressions: log-normal shaped, channel-scaled
    base_impressions = rng.lognormal(mean=10.5, sigma=1.2, size=n_rows).astype(int)
    impressions = np.clip(
        (base_impressions * np.array([CHANNEL_IMPRESSIONS_SCALE[c] for c in channels])).astype(int),
        1000, 500000,
    )

    # inject 0.3% impressions outliers (100× normal)
    n_imp_outliers = max(1, int(n_rows * 0.003))
    imp_outlier_idx = rng.choice(n_rows, size=n_imp_outliers, replace=False)
    impressions[imp_outlier_idx] = np.clip(impressions[imp_outlier_idx] * 100, 1, 50_000_000)

    # clicks from CTR
    ctr_noise = rng.uniform(0.7, 1.3, size=n_rows)
    ctrs = np.array([CHANNEL_CTR[c] for c in channels]) * ctr_noise
    clicks = np.maximum(1, (impressions * ctrs).astype(int))

    # inject outage: 1 specific day in Q3 all clicks = 0
    if quarter_start == "2024-07-01":
        outage_date = np.datetime64("2024-08-14")
        outage_mask = row_dates == outage_date
        clicks[outage_mask] = 0

    # conversions
    cvr = rng.uniform(0.01, 0.08, size=n_rows)
    conversions = np.maximum(0, (clicks * cvr).astype(int))

    # spend: log-normal, $50-$50k
    spend_usd = np.clip(rng.lognormal(mean=7.5, sigma=1.1, size=n_rows), 50, 50_000).round(2)

    # inject 0.5% spend outliers (10× normal)
    n_spend_outliers = max(1, int(n_rows * 0.005))
    spend_outlier_idx = rng.choice(n_rows, size=n_spend_outliers, replace=False)
    spend_usd[spend_outlier_idx] = np.clip(spend_usd[spend_outlier_idx] * 10, 500, 500_000)

    # revenue from conversions × AOV
    aov = np.array([
        AOV_BASE[pr] * TIER_MULTIPLIER[PROFESSION_TIER[p]] * rng.uniform(0.8, 1.2)
        for pr, p in zip(price_ranges, professions)
    ])
    revenue_usd = (conversions * aov).round(2)

    # inject 0.2% negative ROI rows (refunds exceed revenue — negative revenue)
    n_roi_outliers = max(1, int(n_rows * 0.002))
    roi_outlier_idx = rng.choice(n_rows, size=n_roi_outliers, replace=False)
    revenue_usd[roi_outlier_idx] = -spend_usd[roi_outlier_idx] * rng.uniform(0.1, 0.5, size=n_roi_outliers)

    roi = np.where(spend_usd > 0, revenue_usd / spend_usd, 0.0).round(4)

    quality_score: np.ndarray = rng.integers(1, 11, size=n_rows).astype(float)

    # inject 5% NULL quality_score in Q2 only
    if quarter_start == "2024-04-01":
        n_null_qs = int(n_rows * 0.05)
        null_qs_idx = rng.choice(n_rows, size=n_null_qs, replace=False)
        quality_score[null_qs_idx] = np.nan

    campaign_ids = [f"MC-{i:05d}" for i in range(seed_offset * 10000 + 1, seed_offset * 10000 + n_rows + 1)]

    df = pd.DataFrame({
        "campaign_id": campaign_ids,
        "date": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in row_dates],
        "geo": geos,
        "city": cities,
        "profession": professions,
        "price_range": price_ranges,
        "language": languages,
        "channel": channels,
        "campaign_type": campaign_types,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "spend_usd": spend_usd,
        "revenue_usd": revenue_usd,
        "roi": roi,
        "quality_score": quality_score,
    })

    return df.sort_values("date").reset_index(drop=True)


def generate_gig_prices(
    quarter_start: str,
    quarter_end: str,
    seed_offset: int,
    vendor_competition_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Daily snapshot of avg/median/min/max gig prices per category.

    Causal signals:
    - n_active_vendors ↑ → price ↓ (competition suppression, same day with lag in discovery)
    - price drops during SALE_PERIODS → transaction volume ↑ (1-week lag in generate_transactions)
    DQ injections: 0.3% price outliers (10×), 0.5% NULL avg_price_usd.
    """
    rng = _rng_for(seed_offset)
    dates = pd.date_range(quarter_start, quarter_end)
    sale_ranges = [
        (pd.Timestamp(s), pd.Timestamp(e), disc)
        for s, e, _, disc in SALE_PERIODS
    ]

    # Pre-build vendor lookup: (date_str, category) → n_active_vendors
    vendor_lookup: dict[tuple[str, str], int] = {}
    if vendor_competition_df is not None:
        valid_vc = vendor_competition_df[vendor_competition_df["n_active_vendors"] > 0]
        vendor_lookup = dict(zip(
            zip(valid_vc["date"].astype(str), valid_vc["gig_category"]),
            valid_vc["n_active_vendors"].astype(int),
        ))

    rows = []
    for date in dates:
        discount = 0.0
        discount_active = False
        for sale_start, sale_end, disc in sale_ranges:
            if sale_start <= date <= sale_end:
                discount = disc
                discount_active = True
                break

        days_since_epoch = (date - pd.Timestamp("2024-01-01")).days
        trend = 1.0 + 0.00020 * days_since_epoch   # ~7 % annual price inflation

        month = date.month
        seasonal = 1.05 if month in (4, 5, 6) else (0.95 if month in (10, 11, 12) else 1.0)
        sale_factor = 1.0 - discount
        date_str = date.strftime("%Y-%m-%d")

        for cat in GIG_CATEGORIES:
            # Competition factor: more vendors → lower prices (up to -18%, up to +6% if scarcity)
            n_vendors = vendor_lookup.get((date_str, cat), N_VENDORS_BASE[cat])
            vendor_surplus = (n_vendors - N_VENDORS_BASE[cat]) / N_VENDORS_BASE[cat]
            competition_factor = 1.0 - float(np.clip(0.65 * vendor_surplus, -0.06, 0.18))

            base = GIG_PRICE_BASE[cat]
            noise = rng.uniform(0.88, 1.12)
            avg_price = base * trend * seasonal * sale_factor * competition_factor * noise
            spread = avg_price * rng.uniform(0.12, 0.28)
            rows.append({
                "date":              date.strftime("%Y-%m-%d"),
                "gig_category":      cat,
                "avg_price_usd":     round(avg_price, 2),
                "median_price_usd":  round(avg_price * rng.uniform(0.92, 1.08), 2),
                "min_price_usd":     round(max(5.0, avg_price - spread * 2.2), 2),
                "max_price_usd":     round(avg_price + spread * rng.uniform(1.8, 4.5), 2),
                "n_listings":        max(10, int(rng.lognormal(
                                         np.log(N_LISTINGS_BASE[cat]), 0.35))),
                "discount_active":   discount_active,
            })

    df = pd.DataFrame(rows)

    # price_change_pct vs 7 days prior (requires full series to be sorted)
    df = df.sort_values(["gig_category", "date"]).reset_index(drop=True)
    df["price_change_pct"] = (
        df.groupby("gig_category")["avg_price_usd"]
          .pct_change(periods=7)
          .mul(100)
          .round(2)
    )

    # Inject DQ issues
    n_outliers = max(1, int(len(df) * 0.003))
    oi = rng.choice(len(df), size=n_outliers, replace=False)
    df.loc[oi, "avg_price_usd"] = (
        df.loc[oi, "avg_price_usd"] * rng.uniform(8, 15, size=n_outliers)
    ).round(2)

    n_null = max(1, int(len(df) * 0.005))
    ni = rng.choice(len(df), size=n_null, replace=False)
    df.loc[ni, "avg_price_usd"] = np.nan

    return df.sort_values(["date", "gig_category"]).reset_index(drop=True)


def _build_weekly_avg_price(gig_prices_df: pd.DataFrame) -> pd.Series:
    """Weekly average gig price (all categories), indexed by ISO week 'YYYY-WW'."""
    prices = gig_prices_df.dropna(subset=["avg_price_usd"]).copy()
    prices["date"] = pd.to_datetime(prices["date"])
    prices["iso_week"] = prices["date"].dt.strftime("%G-%V")
    return prices.groupby("iso_week")["avg_price_usd"].mean()


def _build_weekly_acquisition_spend(marketing_df: pd.DataFrame) -> pd.Series:
    """Compute weekly acquisition spend indexed by ISO week string 'YYYY-WW'."""
    acq = marketing_df[marketing_df["campaign_type"] == "acquisition"].copy()
    acq["date"] = pd.to_datetime(acq["date"])
    acq["iso_week"] = acq["date"].dt.strftime("%G-%V")
    weekly = acq.groupby("iso_week")["spend_usd"].sum()
    return weekly


def generate_transactions(
    quarter_start: str,
    quarter_end: str,
    n_rows: int,
    marketing_df: pd.DataFrame,
    seed_offset: int,
    gig_prices_df: pd.DataFrame | None = None,
    vendor_competition_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rng = _rng_for(seed_offset)
    qstart = pd.Timestamp(quarter_start)
    qend = pd.Timestamp(quarter_end)

    # --- build weekly spend signal (2-week lag) ---
    weekly_spend = _build_weekly_acquisition_spend(marketing_df)

    dates_range = pd.date_range(qstart, qend, freq="D")
    weeks_in_quarter = sorted({d.strftime("%G-%V") for d in dates_range})

    # seasonal multiplier
    quarter_month = qstart.month
    if quarter_month == 10:      # Q4
        season_mult = 1.30
    elif quarter_month == 1:     # Q1
        season_mult = 0.85
    elif quarter_month == 7:     # Q3 summer
        season_mult = 1.10
    else:                        # Q2
        season_mult = 1.0

    # compute target volume per week using the causal formula (2-week lag)
    week_targets: dict[str, float] = {}
    sorted_weeks = sorted(weekly_spend.index.tolist() + weeks_in_quarter)
    all_weeks = sorted(set(sorted_weeks))

    for w in weeks_in_quarter:
        w_ts = pd.to_datetime(w + "-1", format="%G-%V-%u")
        lag2_ts = w_ts - pd.Timedelta(weeks=2)
        lag2_key = lag2_ts.strftime("%G-%V")
        lag_spend = weekly_spend.get(lag2_key, weekly_spend.mean() if len(weekly_spend) else 10000)
        # strong signal: base 200 + 0.003 * lag_spend, then seasonal
        base_vol = (200 + 0.003 * lag_spend) * season_mult
        # add mild noise (10%) so it's not a perfect line
        week_targets[w] = base_vol * rng.uniform(0.90, 1.10)

    # distribute n_rows across weeks proportional to targets
    total_target = sum(week_targets.values())
    week_row_counts: dict[str, int] = {}
    allocated = 0
    week_list = list(week_targets.keys())
    for i, w in enumerate(week_list[:-1]):
        count = int(n_rows * week_targets[w] / total_target)
        week_row_counts[w] = count
        allocated += count
    week_row_counts[week_list[-1]] = n_rows - allocated

    # Price causal signal: lower avg gig price → more transactions (1-week lag, bidirectional)
    # High prices (spring) suppress demand; low prices (fall + sales) drive demand.
    if gig_prices_df is not None:
        weekly_price = _build_weekly_avg_price(gig_prices_df)
        baseline_price = float(weekly_price.mean()) if len(weekly_price) else 300.0
        for w in week_targets:
            w_ts = pd.to_datetime(w + "-1", format="%G-%V-%u")
            lag1_key = (w_ts - pd.Timedelta(weeks=1)).strftime("%G-%V")
            lag_price = float(weekly_price.get(lag1_key, baseline_price))
            # bidirectional: positive when price < baseline, negative when price > baseline
            price_effect = (baseline_price - lag_price) / baseline_price
            week_targets[w] = max(30, week_targets[w] + 700.0 * price_effect)

    # Eyeball causal signal: higher profile views → more transactions (1-week lag, bidirectional)
    # Low views (summer) suppress conversions; high views (Q4) drive purchases.
    if vendor_competition_df is not None:
        weekly_views = _build_weekly_profile_views(vendor_competition_df)
        baseline_views = float(weekly_views.mean()) if len(weekly_views) else 1.0
        for w in week_targets:
            w_ts = pd.to_datetime(w + "-1", format="%G-%V-%u")
            lag1_key = (w_ts - pd.Timedelta(weeks=1)).strftime("%G-%V")
            lag1_views = float(weekly_views.get(lag1_key, baseline_views))
            # bidirectional: Q3 low views suppress; Q4 high views boost
            view_effect = (lag1_views - baseline_views) / baseline_views
            week_targets[w] = max(30, week_targets[w] + 600.0 * view_effect)

    # Black Friday / Cyber Monday / New Year spikes in Q4
    spike_dates: set[str] = set()
    if quarter_start == "2024-10-01":
        spike_dates = {"2024-11-29", "2024-12-02", "2024-12-31"}

    rows = []
    txn_counter = seed_offset * 100000 + 1

    for w in week_list:
        w_ts = pd.to_datetime(w + "-1", format="%G-%V-%u")
        w_end = w_ts + pd.Timedelta(days=6)
        w_start_clip = max(w_ts, qstart)
        w_end_clip = min(w_end, qend)
        week_dates = pd.date_range(w_start_clip, w_end_clip)
        if len(week_dates) == 0:
            continue

        count = week_row_counts.get(w, 0)
        if count == 0:
            continue

        # day weights within week (slight weekday bias)
        day_w = np.array([1.2 if d.weekday() < 5 else 0.8 for d in week_dates], dtype=float)
        # apply spike multiplier for special dates
        for idx, d in enumerate(week_dates):
            if d.strftime("%Y-%m-%d") in spike_dates:
                day_w[idx] *= 5.0
        day_w /= day_w.sum()
        row_dates = rng.choice(week_dates, size=count, p=day_w)

        gig_cats = rng.choice(GIG_CATEGORIES, size=count)
        seller_countries = rng.choice(GEOS, size=count, p=GEO_WEIGHTS)
        buyer_countries = rng.choice(GEOS, size=count, p=GEO_WEIGHTS)
        seller_professions = [GIG_TO_PROFESSION[g] for g in gig_cats]

        # amount_usd: log-normal, mostly $50-$500
        amounts = np.clip(rng.lognormal(mean=5.0, sigma=1.2, size=count), 5, 5000).round(2)

        # inject 0.3% enterprise deals ($10k-$50k)
        n_enterprise = max(0, int(count * 0.003))
        if n_enterprise > 0:
            ent_idx = rng.choice(count, size=n_enterprise, replace=False)
            amounts[ent_idx] = rng.uniform(10_000, 50_000, size=n_enterprise).round(2)

        # inject 0.1% data entry errors ($0.01) — ensure at least 1 per ~1000 rows
        n_zero = int(count * 0.001)
        if n_zero < 1 and rng.random() < (count * 0.001):
            n_zero = 1
        if n_zero > 0:
            zero_idx = rng.choice(count, size=n_zero, replace=False)
            amounts[zero_idx] = 0.01

        currencies = rng.choice(CURRENCIES, size=count, p=CURRENCY_WEIGHTS)
        payment_methods = rng.choice(PAYMENT_METHODS, size=count, p=PAYMENT_WEIGHTS)
        statuses = rng.choice(TRANSACTION_STATUSES, size=count, p=STATUS_WEIGHTS)

        # completion_days: varies by gig category
        base_days = np.array([GIG_COMPLETION_DAYS[g] for g in gig_cats], dtype=float)
        completion_days = np.maximum(1, (base_days * rng.lognormal(0.0, 0.4, size=count)).astype(int))
        completion_days = np.clip(completion_days, 1, 30)

        # inject 0.5% project overruns (60-120 days)
        n_overrun = max(0, int(count * 0.005))
        if n_overrun > 0:
            overrun_idx = rng.choice(count, size=n_overrun, replace=False)
            completion_days[overrun_idx] = rng.integers(60, 121, size=n_overrun)

        # ratings: skewed high (beta distribution shifted to 1-5 range), NULL if not completed
        raw_ratings = 1.0 + 4.0 * rng.beta(a=5.0, b=1.5, size=count)
        ratings = np.round(np.clip(raw_ratings, 1.0, 5.0), 1)

        # inject 1% rating=1.0 with completed status (unhappy customers)
        n_unhappy = max(0, int(count * 0.01))
        if n_unhappy > 0:
            completed_mask = np.where(statuses == "completed")[0]
            if len(completed_mask) >= n_unhappy:
                unhappy_idx = rng.choice(completed_mask, size=n_unhappy, replace=False)
                ratings[unhappy_idx] = 1.0

        # NULL ratings for non-completed transactions
        ratings = ratings.astype(object)
        for j in range(count):
            if statuses[j] != "completed":
                ratings[j] = None

        is_repeat_buyer = rng.random(size=count) < 0.35
        platform_fees = (amounts * 0.20).round(2)
        seller_levels = rng.choice(SELLER_LEVELS, size=count, p=SELLER_LEVEL_WEIGHTS)
        week_numbers = [pd.Timestamp(d).isocalendar()[1] for d in row_dates]

        for j in range(count):
            rows.append({
                "transaction_id": f"TXN-{txn_counter:06d}",
                "date": pd.Timestamp(row_dates[j]).strftime("%Y-%m-%d"),
                "gig_category": gig_cats[j],
                "seller_country": seller_countries[j],
                "buyer_country": buyer_countries[j],
                "seller_profession": seller_professions[j],
                "amount_usd": amounts[j],
                "currency": currencies[j],
                "payment_method": payment_methods[j],
                "status": statuses[j],
                "completion_days": completion_days[j],
                "rating": ratings[j],
                "is_repeat_buyer": bool(is_repeat_buyer[j]),
                "platform_fee_usd": platform_fees[j],
                "seller_level": seller_levels[j],
                "week_number": week_numbers[j],
            })
            txn_counter += 1

    df = pd.DataFrame(rows)
    return df.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    # 1. Marketing campaigns
    all_marketing = []
    for i, (qs, qe) in enumerate(QUARTERS):
        df = generate_marketing_campaigns(qs, qe, 3000, seed_offset=i)
        all_marketing.append(df)
        df.to_csv(OUTPUT_DIR / f"marketing_campaigns_{QUARTER_NAMES[i]}.csv", index=False)
        print(f"Written marketing_campaigns_{QUARTER_NAMES[i]}.csv ({len(df)} rows)")
    all_marketing_df = pd.concat(all_marketing, ignore_index=True)

    # 2. Vendor competition (drives gig prices and transaction eyeballs)
    all_vendor = []
    for i, (qs, qe) in enumerate(QUARTERS):
        df = generate_vendor_competition(qs, qe, seed_offset=i + 40)
        all_vendor.append(df)
        df.to_csv(OUTPUT_DIR / f"gig_vendor_stats_{QUARTER_NAMES[i]}.csv", index=False)
        print(f"Written gig_vendor_stats_{QUARTER_NAMES[i]}.csv ({len(df)} rows)")
    all_vendor_df = pd.concat(all_vendor, ignore_index=True)

    # 3. Gig prices (driven by vendor competition + sale periods)
    all_gig_prices = []
    for i, (qs, qe) in enumerate(QUARTERS):
        df = generate_gig_prices(qs, qe, seed_offset=i + 20, vendor_competition_df=all_vendor_df)
        all_gig_prices.append(df)
        df.to_csv(OUTPUT_DIR / f"gig_prices_{QUARTER_NAMES[i]}.csv", index=False)
        print(f"Written gig_prices_{QUARTER_NAMES[i]}.csv ({len(df)} rows)")
    all_gig_prices_df = pd.concat(all_gig_prices, ignore_index=True)

    # 4. Transactions (driven by marketing spend, gig prices, and vendor eyeballs)
    for i, (qs, qe) in enumerate(QUARTERS):
        df = generate_transactions(
            qs, qe, 4000, all_marketing_df,
            seed_offset=i + 10,
            gig_prices_df=all_gig_prices_df,
            vendor_competition_df=all_vendor_df,
        )
        df.to_csv(OUTPUT_DIR / f"gigler_transactions_{QUARTER_NAMES[i]}.csv", index=False)
        print(f"Written gigler_transactions_{QUARTER_NAMES[i]}.csv ({len(df)} rows)")

    print("Done.")

#!/usr/bin/env python3
"""
Generate sample data for Gigler + marketing campaigns demo.
Run: python examples/gigler/generate_data.py

Causality: acquisition campaign spend → transaction volume with 2-week lag.
Signal is strong enough for Granger causality detection (designed correlation > 0.6).
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


def _rng_for(seed_offset: int) -> np.random.Generator:
    return np.random.default_rng(42 + seed_offset * 97)


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
    all_marketing = []
    for i, (qs, qe) in enumerate(QUARTERS):
        df = generate_marketing_campaigns(qs, qe, 3000, seed_offset=i)
        all_marketing.append(df)
        df.to_csv(OUTPUT_DIR / f"marketing_campaigns_{QUARTER_NAMES[i]}.csv", index=False)
        print(f"Written marketing_campaigns_{QUARTER_NAMES[i]}.csv ({len(df)} rows)")

    all_marketing_df = pd.concat(all_marketing, ignore_index=True)

    for i, (qs, qe) in enumerate(QUARTERS):
        df = generate_transactions(qs, qe, 4000, all_marketing_df, seed_offset=i + 10)
        df.to_csv(OUTPUT_DIR / f"gigler_transactions_{QUARTER_NAMES[i]}.csv", index=False)
        print(f"Written gigler_transactions_{QUARTER_NAMES[i]}.csv ({len(df)} rows)")

    print("Done.")

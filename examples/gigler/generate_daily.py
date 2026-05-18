#!/usr/bin/env python3
"""Generate daily Gigler demo data and append it to BigQuery.

On first run backfills all days from (last existing date + 1) up to today.
On subsequent runs adds just the next missing day, so it is safe to schedule.
Idempotent: checks BigQuery before inserting.

Usage:
    python examples/gigler/generate_daily.py \
        --credentials examples/gigler/application_default_credentials.json

    # Generate up to a specific date instead of today:
    python examples/gigler/generate_daily.py \
        --credentials examples/gigler/application_default_credentials.json \
        --until 2025-06-30

Requires:
    pip install google-cloud-bigquery
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _load(table: str) -> list[dict]:
    path = DATA_DIR / f"{table}.csv"
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _latest_date(rows: list[dict]) -> date:
    return max(date.fromisoformat(r["date"]) for r in rows)


def _rows_on(rows: list[dict], d: date) -> list[dict]:
    s = str(d)
    return [r for r in rows if r["date"] == s]


def _walk(value: str, rng: random.Random, pct: float = 0.04) -> str:
    """Apply a multiplicative random walk of ±pct to a numeric string.
    Preserves integer type if the original value has no decimal point.
    """
    try:
        f = float(value)
        result = f * (1.0 + rng.uniform(-pct, pct))
        # If original was an integer, keep it an integer
        if "." not in value:
            return str(max(0, round(result)))
        return str(round(result, 6))
    except (ValueError, TypeError):
        return value


def _rows_to_csv_bytes(rows: list[dict], fieldnames: list[str]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode()


# ------------------------------------------------------------------ #
# Per-table generators                                                 #
# ------------------------------------------------------------------ #

def _gen_gig_prices(target: date, rng: random.Random, source_rows: list[dict]) -> list[dict]:
    """Walk forward from the most recent day -- one row per category."""
    last = _rows_on(source_rows, _latest_date(source_rows))
    new = []
    for row in last:
        r = dict(row)
        r["date"] = str(target)
        # Numeric walk
        for col in ("avg_price_usd", "median_price_usd", "min_price_usd",
                    "max_price_usd", "n_listings"):
            r[col] = _walk(r[col], rng, 0.03)
        # price_change_pct: difference from previous avg (small random)
        r["price_change_pct"] = str(round(rng.gauss(0, 0.015), 4))
        # discount_active: small chance to flip
        if rng.random() < 0.05:
            r["discount_active"] = "False" if r["discount_active"] == "True" else "True"
        new.append(r)
    return new


def _gen_gig_vendor_stats(target: date, rng: random.Random, source_rows: list[dict]) -> list[dict]:
    last = _rows_on(source_rows, _latest_date(source_rows))
    new = []
    for row in last:
        r = dict(row)
        r["date"] = str(target)
        for col in ("n_active_vendors", "n_new_vendors", "avg_vendor_rating",
                    "top_rated_fraction", "total_profile_views", "avg_profile_views",
                    "search_impressions", "click_through_rate", "avg_response_time_hours"):
            if r.get(col, "") == "":
                continue
            r[col] = _walk(r[col], rng, 0.04)
        new.append(r)
    return new


def _gen_marketing_campaigns(
    target: date, rng: random.Random, source_rows: list[dict], next_campaign_id: int
) -> tuple[list[dict], int]:
    last = _rows_on(source_rows, _latest_date(source_rows))
    new = []
    cid = next_campaign_id
    for row in last:
        r = dict(row)
        r["date"] = str(target)
        r["campaign_id"] = f"MC-{cid:05d}"
        cid += 1
        # Walk impressions, clicks, conversions
        impressions = max(1, round(float(r["impressions"]) * (1 + rng.uniform(-0.05, 0.05))))
        clicks = max(0, round(float(r["clicks"]) * (1 + rng.uniform(-0.05, 0.05))))
        clicks = min(clicks, impressions)
        conversions = max(0, round(float(r["conversions"]) * (1 + rng.uniform(-0.08, 0.08))))
        conversions = min(conversions, clicks)
        spend = round(float(r["spend_usd"]) * (1 + rng.uniform(-0.04, 0.04)), 2)
        revenue = round(float(r["revenue_usd"]) * (1 + rng.uniform(-0.06, 0.06)), 2)
        r["impressions"] = str(impressions)
        r["clicks"] = str(clicks)
        r["conversions"] = str(conversions)
        r["spend_usd"] = str(spend)
        r["revenue_usd"] = str(revenue)
        r["roi"] = str(round(revenue / spend, 4)) if spend > 0 else "0"
        r["quality_score"] = _walk(r["quality_score"], rng, 0.02)
        new.append(r)
    return new, cid


def _gen_transactions(
    target: date, rng: random.Random, source_rows: list[dict], next_txn_id: int
) -> tuple[list[dict], int]:
    # Weighted pools from full history
    categories   = [r["gig_category"]    for r in source_rows]
    sell_ctries  = [r["seller_country"]  for r in source_rows]
    buy_ctries   = [r["buyer_country"]   for r in source_rows]
    professions  = [r["seller_profession"] for r in source_rows]
    currencies   = [r["currency"]        for r in source_rows]
    methods      = [r["payment_method"]  for r in source_rows]
    statuses     = [r["status"]          for r in source_rows]
    levels       = [r["seller_level"]    for r in source_rows]
    comp_days    = [int(r["completion_days"]) for r in source_rows]
    ratings      = [float(r["rating"])   for r in source_rows if r.get("rating")]
    amounts      = [float(r["amount_usd"]) for r in source_rows if r.get("amount_usd")]

    mu  = statistics.mean(amounts)
    sig = statistics.stdev(amounts)

    # Average transactions per day from history
    daily_counts = defaultdict(int)
    for r in source_rows:
        daily_counts[r["date"]] += 1
    avg_per_day = statistics.mean(daily_counts.values())
    n = max(20, round(rng.gauss(avg_per_day, avg_per_day * 0.1)))

    week_num = target.isocalendar()[1]
    new = []
    tid = next_txn_id
    for _ in range(n):
        amount = round(max(5.0, min(15000.0, abs(rng.gauss(mu, sig)))), 2)
        new.append({
            "transaction_id":  f"TXN-{tid:07d}",
            "date":            str(target),
            "gig_category":    rng.choice(categories),
            "seller_country":  rng.choice(sell_ctries),
            "buyer_country":   rng.choice(buy_ctries),
            "seller_profession": rng.choice(professions),
            "amount_usd":      str(amount),
            "currency":        rng.choice(currencies),
            "payment_method":  rng.choice(methods),
            "status":          rng.choice(statuses),
            "completion_days": str(rng.choice(comp_days)),
            "rating":          str(round(rng.choice(ratings), 1)),
            "is_repeat_buyer": str(rng.random() < 0.30),
            "platform_fee_usd": str(round(amount * 0.20, 2)),
            "seller_level":    rng.choice(levels),
            "week_number":     str(week_num),
        })
        tid += 1
    return new, tid


# ------------------------------------------------------------------ #
# BigQuery helpers                                                      #
# ------------------------------------------------------------------ #

def _bq_latest_date(client, table_id: str) -> date | None:
    """Return the most recent date present in a BigQuery table, or None."""
    from google.cloud.exceptions import NotFound
    try:
        row = next(iter(client.query(f"SELECT MAX(date) FROM `{table_id}`").result()))
        return row[0]  # BigQuery DATE -> datetime.date
    except NotFound:
        return None


def _date_exists(client, table_id: str, d: date) -> bool:
    from google.cloud.exceptions import NotFound
    try:
        result = client.query(
            f"SELECT COUNT(*) FROM `{table_id}` WHERE date = '{d}'"
        ).result()
        return next(iter(result))[0] > 0
    except NotFound:
        return False


def _append(client, table_id: str, rows: list[dict], fieldnames: list[str]) -> None:
    from google.cloud import bigquery
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=False,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    data = _rows_to_csv_bytes(rows, fieldnames)
    client.load_table_from_file(io.BytesIO(data), table_id, job_config=job_config).result()


# ------------------------------------------------------------------ #
# Main                                                                 #
# ------------------------------------------------------------------ #

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate daily Gigler demo data into BigQuery")
    parser.add_argument("--credentials", required=True, help="Path to credentials JSON")
    parser.add_argument("--project", default=None, help="GCP project ID (default: quota_project_id from credentials)")
    parser.add_argument("--dataset", default="gigler", help="BigQuery dataset (default: gigler)")
    parser.add_argument("--until", default=None, help="Generate up to this date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    creds_path = Path(args.credentials)
    if not creds_path.exists():
        sys.exit(f"Credentials file not found: {creds_path}")

    project = args.project
    if not project:
        with open(creds_path) as f:
            project = json.load(f).get("quota_project_id")
    if not project:
        sys.exit("Could not determine project ID -- pass --project or add quota_project_id to credentials")

    until = date.fromisoformat(args.until) if args.until else date.today()

    try:
        import google.auth
        from google.cloud import bigquery
    except ImportError:
        sys.exit("Missing dependency -- run: pip install google-cloud-bigquery")

    credentials, _ = google.auth.load_credentials_from_file(
        str(creds_path),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    client = bigquery.Client(credentials=credentials, project=project)

    # Load source CSVs once (used for distributions / random walk baseline)
    txn_rows   = _load("gigler_transactions")
    price_rows = _load("gig_prices")
    vstats_rows = _load("gig_vendor_stats")
    camp_rows  = _load("marketing_campaigns")

    # Determine start date from BigQuery (authoritative), fall back to CSV
    bq_dates = [
        _bq_latest_date(client, f"{project}.{args.dataset}.{t}")
        for t in ("gigler_transactions", "gig_prices", "gig_vendor_stats", "marketing_campaigns")
    ]
    bq_dates = [d for d in bq_dates if d is not None]
    if bq_dates:
        last_date = max(bq_dates)
        print(f"Last date in BigQuery: {last_date}")
    else:
        last_date = max(
            _latest_date(txn_rows), _latest_date(price_rows),
            _latest_date(vstats_rows), _latest_date(camp_rows),
        )
        print(f"No data in BigQuery yet -- starting from CSV last date: {last_date}")

    # Determine date range to generate
    start = last_date + timedelta(days=1)
    if start > until:
        print(f"Data already up to date (last date: {last_date}, until: {until})")
        return

    days = (until - start).days + 1
    print(f"Generating {days} day(s): {start} to {until}")

    # Next available IDs
    next_txn_id  = max(int(r["transaction_id"].replace("TXN-", "")) for r in txn_rows) + 1
    next_camp_id = max(int(r["campaign_id"].replace("MC-", ""))      for r in camp_rows) + 1

    tables = {
        "gigler_transactions": list(txn_rows[0].keys()),
        "gig_prices":          list(price_rows[0].keys()),
        "gig_vendor_stats":    list(vstats_rows[0].keys()),
        "marketing_campaigns": list(camp_rows[0].keys()),
    }

    current = start
    while current <= until:
        seed = int(current.strftime("%Y%m%d"))
        rng = random.Random(seed)

        print(f"\n  {current}", end="  ", flush=True)

        for table, fieldnames in tables.items():
            tid = f"{project}.{args.dataset}.{table}"
            if _date_exists(client, tid, current):
                print(f"{table}:skip ", end="", flush=True)
                continue

            if table == "gigler_transactions":
                rows, next_txn_id = _gen_transactions(current, rng, txn_rows, next_txn_id)
            elif table == "gig_prices":
                rows = _gen_gig_prices(current, rng, price_rows)
                price_rows += rows          # extend in-memory for next day's walk
            elif table == "gig_vendor_stats":
                rows = _gen_gig_vendor_stats(current, rng, vstats_rows)
                vstats_rows += rows
            elif table == "marketing_campaigns":
                rows, next_camp_id = _gen_marketing_campaigns(current, rng, camp_rows, next_camp_id)
                camp_rows += rows

            _append(client, tid, rows, fieldnames)
            print(f"{table}:{len(rows)} ", end="", flush=True)

        current += timedelta(days=1)

    print("\n\nDone.")


if __name__ == "__main__":
    main()

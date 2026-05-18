#!/usr/bin/env python3
"""Bring Gigler CSVs up to today, then load everything into BigQuery.

Steps:
  1. Find the latest date already in each local CSV file.
  2. Generate rows for every missing day up to today and append them to the CSVs.
  3. Load each full CSV into BigQuery with WRITE_TRUNCATE (replaces the table).

This is the only script you need to run after the initial seed
(generate_data.py + combine_csv.py).  It is safe to re-run at any time.

Usage:
    python examples/gigler/load_to_bigquery.py \
        --credentials examples/gigler/application_default_credentials.json

    # Custom dataset or target date:
    python examples/gigler/load_to_bigquery.py \
        --credentials examples/gigler/application_default_credentials.json \
        --dataset gigler_staging \
        --until 2025-12-31

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
_SHARD_RE = re.compile(r"_\d{4}_q\d$", re.IGNORECASE)

TABLE_NAMES = ["gigler_transactions", "gig_prices", "gig_vendor_stats", "marketing_campaigns"]


# ------------------------------------------------------------------ #
# CSV helpers                                                          #
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


def _append_to_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        w.writerows(rows)


# ------------------------------------------------------------------ #
# Random walk                                                          #
# ------------------------------------------------------------------ #

def _walk(value: str, rng: random.Random, pct: float = 0.04) -> str:
    """Multiplicative random walk of ±pct. Preserves integer type."""
    try:
        f = float(value)
        result = f * (1.0 + rng.uniform(-pct, pct))
        if "." not in value:
            return str(max(0, round(result)))
        return str(round(result, 6))
    except (ValueError, TypeError):
        return value


# ------------------------------------------------------------------ #
# Per-table generators                                                 #
# ------------------------------------------------------------------ #

def _gen_gig_prices(target: date, rng: random.Random, source_rows: list[dict]) -> list[dict]:
    last = _rows_on(source_rows, _latest_date(source_rows))
    new = []
    for row in last:
        r = dict(row)
        r["date"] = str(target)
        for col in ("avg_price_usd", "median_price_usd", "min_price_usd", "max_price_usd", "n_listings"):
            r[col] = _walk(r[col], rng, 0.03)
        r["price_change_pct"] = str(round(rng.gauss(0, 0.015), 4))
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
        impressions = max(1, round(float(r["impressions"]) * (1 + rng.uniform(-0.05, 0.05))))
        clicks = min(max(0, round(float(r["clicks"]) * (1 + rng.uniform(-0.05, 0.05)))), impressions)
        conversions = min(max(0, round(float(r["conversions"]) * (1 + rng.uniform(-0.08, 0.08)))), clicks)
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
    categories  = [r["gig_category"]        for r in source_rows]
    sell_ctries = [r["seller_country"]      for r in source_rows]
    buy_ctries  = [r["buyer_country"]       for r in source_rows]
    professions = [r["seller_profession"]   for r in source_rows]
    currencies  = [r["currency"]            for r in source_rows]
    methods     = [r["payment_method"]      for r in source_rows]
    statuses    = [r["status"]              for r in source_rows]
    levels      = [r["seller_level"]        for r in source_rows]
    comp_days   = [int(r["completion_days"]) for r in source_rows]
    ratings     = [float(r["rating"])       for r in source_rows if r.get("rating")]
    amounts     = [float(r["amount_usd"])   for r in source_rows if r.get("amount_usd")]

    mu, sig = statistics.mean(amounts), statistics.stdev(amounts)

    daily_counts: dict[str, int] = defaultdict(int)
    for r in source_rows:
        daily_counts[r["date"]] += 1
    avg_per_day = statistics.mean(daily_counts.values())
    n = max(20, round(rng.gauss(avg_per_day, avg_per_day * 0.1)))

    week_num = target.isocalendar()[1]
    new, tid = [], next_txn_id
    for _ in range(n):
        amount = round(max(5.0, min(15000.0, abs(rng.gauss(mu, sig)))), 2)
        new.append({
            "transaction_id":    f"TXN-{tid:07d}",
            "date":              str(target),
            "gig_category":      rng.choice(categories),
            "seller_country":    rng.choice(sell_ctries),
            "buyer_country":     rng.choice(buy_ctries),
            "seller_profession": rng.choice(professions),
            "amount_usd":        str(amount),
            "currency":          rng.choice(currencies),
            "payment_method":    rng.choice(methods),
            "status":            rng.choice(statuses),
            "completion_days":   str(rng.choice(comp_days)),
            "rating":            str(round(rng.choice(ratings), 1)),
            "is_repeat_buyer":   str(rng.random() < 0.30),
            "platform_fee_usd":  str(round(amount * 0.20, 2)),
            "seller_level":      rng.choice(levels),
            "week_number":       str(week_num),
        })
        tid += 1
    return new, tid


# ------------------------------------------------------------------ #
# BigQuery helpers                                                     #
# ------------------------------------------------------------------ #

def _ensure_dataset(client, project: str, dataset_name: str) -> None:
    from google.cloud import bigquery
    from google.cloud.exceptions import NotFound
    ref = bigquery.Dataset(f"{project}.{dataset_name}")
    ref.location = "US"
    try:
        client.get_dataset(ref)
        print(f"  dataset {project}.{dataset_name} already exists")
    except NotFound:
        client.create_dataset(ref)
        print(f"  created dataset {project}.{dataset_name}")


def _load_csv_truncate(client, table_id: str, csv_path: Path) -> None:
    from google.cloud import bigquery
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    with csv_path.open("rb") as f:
        client.load_table_from_file(f, table_id, job_config=job_config).result()
    table = client.get_table(table_id)
    print(f"  {csv_path.name:<40} {table.num_rows:>8,} rows -> {table_id}")


# ------------------------------------------------------------------ #
# Main                                                                 #
# ------------------------------------------------------------------ #

def main() -> None:
    parser = argparse.ArgumentParser(description="Extend Gigler CSVs to today and load into BigQuery")
    parser.add_argument("--credentials", required=True, help="Path to credentials JSON")
    parser.add_argument("--project", default=None, help="GCP project ID (default: from credentials)")
    parser.add_argument("--dataset", default="gigler", help="BigQuery dataset (default: gigler)")
    parser.add_argument("--until", default=None, help="Generate up to YYYY-MM-DD (default: today)")
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
        str(creds_path), scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    client = bigquery.Client(credentials=credentials, project=project)

    # ---- Step 1: load CSVs and find the gap ----
    print("Loading local CSV files...")
    txn_rows    = _load("gigler_transactions")
    price_rows  = _load("gig_prices")
    vstats_rows = _load("gig_vendor_stats")
    camp_rows   = _load("marketing_campaigns")

    fieldnames = {
        "gigler_transactions": list(txn_rows[0].keys()),
        "gig_prices":          list(price_rows[0].keys()),
        "gig_vendor_stats":    list(vstats_rows[0].keys()),
        "marketing_campaigns": list(camp_rows[0].keys()),
    }

    csv_last = {
        "gigler_transactions": _latest_date(txn_rows),
        "gig_prices":          _latest_date(price_rows),
        "gig_vendor_stats":    _latest_date(vstats_rows),
        "marketing_campaigns": _latest_date(camp_rows),
    }
    for t, d in csv_last.items():
        print(f"  {t:<30} last date in CSV: {d}")

    last_date = min(csv_last.values())  # fill the most-behind table
    start = last_date + timedelta(days=1)

    if start > until:
        print(f"\nCSVs already up to date (last date: {last_date})")
    else:
        days = (until - start).days + 1
        print(f"\nGenerating {days} day(s): {start} to {until}")

        # Starting IDs: take max from CSV so we never collide
        next_txn_id  = max(int(r["transaction_id"].replace("TXN-", "")) for r in txn_rows)  + 1
        next_camp_id = max(int(r["campaign_id"].replace("MC-", ""))      for r in camp_rows) + 1

        # ---- Step 2: generate new rows ----
        new_rows: dict[str, list[dict]] = {t: [] for t in TABLE_NAMES}

        current = start
        while current <= until:
            rng = random.Random(int(current.strftime("%Y%m%d")))

            # transactions
            txn, next_txn_id = _gen_transactions(current, rng, txn_rows, next_txn_id)
            if current > csv_last["gigler_transactions"]:
                new_rows["gigler_transactions"].extend(txn)

            # prices — always advance walk baseline
            prices = _gen_gig_prices(current, rng, price_rows)
            price_rows += prices
            if current > csv_last["gig_prices"]:
                new_rows["gig_prices"].extend(prices)

            # vendor stats — always advance walk baseline
            vstats = _gen_gig_vendor_stats(current, rng, vstats_rows)
            vstats_rows += vstats
            if current > csv_last["gig_vendor_stats"]:
                new_rows["gig_vendor_stats"].extend(vstats)

            # campaigns — always advance walk baseline
            camps, next_camp_id = _gen_marketing_campaigns(current, rng, camp_rows, next_camp_id)
            camp_rows += camps
            if current > csv_last["marketing_campaigns"]:
                new_rows["marketing_campaigns"].extend(camps)

            current += timedelta(days=1)

        for t in TABLE_NAMES:
            print(f"  {t:<30} +{len(new_rows[t]):>7,} new rows")

        # ---- Step 3: append new rows to CSV files ----
        print("\nAppending to CSV files...")
        for t in TABLE_NAMES:
            if not new_rows[t]:
                continue
            _append_to_csv(DATA_DIR / f"{t}.csv", new_rows[t], fieldnames[t])
            print(f"  {t}.csv  +{len(new_rows[t]):,} rows")

    # ---- Step 4: load full CSVs into BigQuery (WRITE_TRUNCATE) ----
    print("\nLoading CSVs into BigQuery (WRITE_TRUNCATE)...")
    _ensure_dataset(client, project, args.dataset)
    for t in TABLE_NAMES:
        csv_path = DATA_DIR / f"{t}.csv"
        if not csv_path.exists():
            print(f"  SKIP {t}.csv (not found)")
            continue
        _load_csv_truncate(client, f"{project}.{args.dataset}.{t}", csv_path)

    print("\nDone.")


if __name__ == "__main__":
    main()

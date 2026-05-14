#!/usr/bin/env python3
"""Seed the dqt database with Gigler ClickHouse data: source, datasets, columns,
column profiles, checks, check runs, incidents, metrics, causal edges.

Usage:
    python tmp/seed_gigler.py [DATABASE_URL]
    # default: postgresql://dqt:dqtdev@localhost:5434/dqt
"""
from __future__ import annotations

import sys
import uuid
import datetime as dt
import json
import math
import random
import psycopg2
import psycopg2.extras

DATABASE_URL = sys.argv[1] if len(sys.argv) > 1 else "postgresql://dqt:dqtdev@localhost:5434/dqt"
TENANT_ID = "default"
SOURCE_ID = "299b4839-1146-4474-93d6-06410389aa8f"  # Gigler ClickHouse (already inserted)
OWNER = "anton@freightos.com"

random.seed(42)

def uid() -> str:
    return str(uuid.uuid4())

def now() -> str:
    return dt.datetime.utcnow().isoformat()

def days_ago(n: int) -> str:
    return (dt.datetime.utcnow() - dt.timedelta(days=n)).isoformat()

def conn_cursor(url):
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ---------------------------------------------------------------------------
# 1. Tenant
# ---------------------------------------------------------------------------
def seed_tenant(cur):
    cur.execute("""
        INSERT INTO tenants (id, slug, name, plan, created_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO NOTHING
    """, (uid(), "default", "dqt default workspace", "pro", days_ago(60)))
    print("  tenant: default")


# ---------------------------------------------------------------------------
# 2. Source (upsert — may already exist)
# ---------------------------------------------------------------------------
def seed_source(cur):
    cur.execute("""
        INSERT INTO sources (id, tenant_id, name, engine, connection_params, credentials_ref,
                             status, owner, tags, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, updated_at = now()
    """, (
        SOURCE_ID, TENANT_ID, "Gigler ClickHouse", "clickhouse",
        json.dumps({"host": "clickhouse-production-bfdb.up.railway.app",
                    "port": 443, "database": "default", "secure": True, "username": "admin"}),
        "CLICKHOUSE_PASSWORD", "healthy", OWNER, ["gigler", "clickhouse", "railway", "example"],
        days_ago(30), now()
    ))
    print(f"  source: Gigler ClickHouse ({SOURCE_ID})")


# ---------------------------------------------------------------------------
# 3. Datasets
# ---------------------------------------------------------------------------
DATASETS = {
    "marketing_campaigns": {
        "row_count": 15000,
        "description": "Marketing campaign performance by channel, geo, and campaign type.",
        "domain": "marketing",
        "tags": ["marketing", "campaigns", "roi"],
        "freshness_sla_seconds": 86400,
    },
    "gigler_transactions": {
        "row_count": 20000,
        "description": "Gig marketplace transactions with ratings, amounts, and status.",
        "domain": "marketplace",
        "tags": ["transactions", "gigs", "ratings"],
        "freshness_sla_seconds": 3600,
    },
    "gig_vendor_stats": {
        "row_count": 6840,
        "description": "Daily vendor activity statistics aggregated by gig category.",
        "domain": "marketplace",
        "tags": ["vendors", "stats", "daily"],
        "freshness_sla_seconds": 86400,
    },
    "gig_prices": {
        "row_count": 6840,
        "description": "Daily price statistics per gig category including min/max/avg.",
        "domain": "marketplace",
        "tags": ["prices", "gigs", "daily"],
        "freshness_sla_seconds": 86400,
    },
}

DATASET_IDS: dict[str, str] = {}

def seed_datasets(cur):
    for tname, meta in DATASETS.items():
        did = uid()
        DATASET_IDS[tname] = did
        cur.execute("""
            INSERT INTO datasets (id, tenant_id, source_id, schema_name, table_name,
                                  row_count, last_profiled_at, freshness_sla_seconds,
                                  owner, domain, description, classification, pii, tags,
                                  created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (source_id, schema_name, table_name) DO UPDATE
            SET row_count=EXCLUDED.row_count, last_profiled_at=EXCLUDED.last_profiled_at, updated_at=now()
            RETURNING id
        """, (
            did, TENANT_ID, SOURCE_ID, "default", tname,
            meta["row_count"], days_ago(1), meta.get("freshness_sla_seconds"),
            OWNER, meta["domain"], meta["description"], "internal", False,
            meta["tags"], days_ago(30), days_ago(1),
        ))
        row = cur.fetchone()
        if row:
            DATASET_IDS[tname] = row["id"]
        print(f"  dataset: {tname} ({DATASET_IDS[tname]})")


# ---------------------------------------------------------------------------
# 4. Columns
# ---------------------------------------------------------------------------
COLUMNS: dict[str, list[dict]] = {
    "marketing_campaigns": [
        {"name": "campaign_id",   "type": "String",        "nullable": True,  "pos": 1},
        {"name": "date",          "type": "DateTime64(3)", "nullable": True,  "pos": 2},
        {"name": "geo",           "type": "String",        "nullable": True,  "pos": 3},
        {"name": "city",          "type": "String",        "nullable": True,  "pos": 4},
        {"name": "profession",    "type": "String",        "nullable": True,  "pos": 5},
        {"name": "price_range",   "type": "String",        "nullable": True,  "pos": 6},
        {"name": "language",      "type": "String",        "nullable": True,  "pos": 7},
        {"name": "channel",       "type": "String",        "nullable": True,  "pos": 8},
        {"name": "campaign_type", "type": "String",        "nullable": True,  "pos": 9},
        {"name": "impressions",   "type": "Int64",         "nullable": True,  "pos": 10},
        {"name": "clicks",        "type": "Int64",         "nullable": True,  "pos": 11},
        {"name": "conversions",   "type": "Int64",         "nullable": True,  "pos": 12},
        {"name": "spend_usd",     "type": "Float64",       "nullable": True,  "pos": 13},
        {"name": "revenue_usd",   "type": "Float64",       "nullable": True,  "pos": 14},
        {"name": "roi",           "type": "Float64",       "nullable": True,  "pos": 15},
        {"name": "quality_score", "type": "Float64",       "nullable": True,  "pos": 16},
    ],
    "gigler_transactions": [
        {"name": "transaction_id",   "type": "String",  "nullable": True,  "pos": 1},
        {"name": "date",             "type": "DateTime64(3)", "nullable": True, "pos": 2},
        {"name": "gig_category",     "type": "String",  "nullable": True,  "pos": 3},
        {"name": "seller_country",   "type": "String",  "nullable": True,  "pos": 4},
        {"name": "buyer_country",    "type": "String",  "nullable": True,  "pos": 5},
        {"name": "seller_profession","type": "String",  "nullable": True,  "pos": 6},
        {"name": "amount_usd",       "type": "Float64", "nullable": True,  "pos": 7},
        {"name": "currency",         "type": "String",  "nullable": True,  "pos": 8},
        {"name": "payment_method",   "type": "String",  "nullable": True,  "pos": 9},
        {"name": "status",           "type": "String",  "nullable": True,  "pos": 10},
        {"name": "completion_days",  "type": "Int64",   "nullable": True,  "pos": 11},
        {"name": "rating",           "type": "Float64", "nullable": True,  "pos": 12},
        {"name": "is_repeat_buyer",  "type": "UInt8",   "nullable": True,  "pos": 13},
        {"name": "platform_fee_usd", "type": "Float64", "nullable": True,  "pos": 14},
        {"name": "seller_level",     "type": "String",  "nullable": True,  "pos": 15},
        {"name": "week_number",      "type": "Int64",   "nullable": True,  "pos": 16},
    ],
    "gig_vendor_stats": [
        {"name": "date",                   "type": "DateTime64(3)", "nullable": True, "pos": 1},
        {"name": "gig_category",           "type": "String",        "nullable": True, "pos": 2},
        {"name": "n_active_vendors",       "type": "Int64",         "nullable": True, "pos": 3},
        {"name": "n_new_vendors",          "type": "Int64",         "nullable": True, "pos": 4},
        {"name": "avg_vendor_rating",      "type": "Float64",       "nullable": True, "pos": 5},
        {"name": "top_rated_fraction",     "type": "Float64",       "nullable": True, "pos": 6},
        {"name": "total_profile_views",    "type": "Float64",       "nullable": True, "pos": 7},
        {"name": "avg_profile_views",      "type": "Float64",       "nullable": True, "pos": 8},
        {"name": "search_impressions",     "type": "Float64",       "nullable": True, "pos": 9},
        {"name": "click_through_rate",     "type": "Float64",       "nullable": True, "pos": 10},
        {"name": "avg_response_time_hours","type": "Float64",       "nullable": True, "pos": 11},
    ],
    "gig_prices": [
        {"name": "date",             "type": "DateTime64(3)", "nullable": True, "pos": 1},
        {"name": "gig_category",     "type": "String",        "nullable": True, "pos": 2},
        {"name": "avg_price_usd",    "type": "Float64",       "nullable": True, "pos": 3},
        {"name": "median_price_usd", "type": "Float64",       "nullable": True, "pos": 4},
        {"name": "min_price_usd",    "type": "Float64",       "nullable": True, "pos": 5},
        {"name": "max_price_usd",    "type": "Float64",       "nullable": True, "pos": 6},
        {"name": "n_listings",       "type": "Int64",         "nullable": True, "pos": 7},
        {"name": "discount_active",  "type": "UInt8",         "nullable": True, "pos": 8},
        {"name": "price_change_pct", "type": "Float64",       "nullable": True, "pos": 9},
    ],
}

COLUMN_IDS: dict[str, str] = {}  # "table.colname" -> uuid

def seed_columns(cur):
    for tname, cols in COLUMNS.items():
        did = DATASET_IDS[tname]
        for c in cols:
            cid = uid()
            COLUMN_IDS[f"{tname}.{c['name']}"] = cid
            cur.execute("""
                INSERT INTO columns (id, dataset_id, tenant_id, column_name, data_type,
                                     nullable, ordinal_position, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (dataset_id, column_name) DO UPDATE
                SET data_type=EXCLUDED.data_type, updated_at=now()
                RETURNING id
            """, (cid, did, TENANT_ID, c["name"], c["type"],
                  c["nullable"], c["pos"], days_ago(30), days_ago(1)))
            row = cur.fetchone()
            if row:
                COLUMN_IDS[f"{tname}.{c['name']}"] = row["id"]
    print(f"  columns: {len(COLUMN_IDS)} total")


# ---------------------------------------------------------------------------
# 5. Column Profiles (real stats from ClickHouse)
# ---------------------------------------------------------------------------
PROFILES = [
    # marketing_campaigns
    ("marketing_campaigns", "impressions",  "numeric", 15000, 0, 15000,  "1000",  "38957700", 120200.46, 633741.39, 18866.5,  47275.5,  120573.25,
     [{"bin": "<5k", "count": 2843}, {"bin": "5k-50k", "count": 7512}, {"bin": "50k-500k", "count": 4201}, {"bin": ">500k", "count": 444}], None),
    ("marketing_campaigns", "clicks",       "numeric", 15000, 0, 15000,  "0",     "2130648",  3480.89,   25404.82,  511.0,    1294.0,   3419.75,
     [{"bin": "<100", "count": 1820}, {"bin": "100-1k", "count": 5632}, {"bin": "1k-10k", "count": 6841}, {"bin": ">10k", "count": 707}], None),
    ("marketing_campaigns", "spend_usd",    "numeric", 15000, 0, None,   "50.0",  "184789.2", 3479.75,   6122.13,   850.03,   1795.54,  3857.40,
     [{"bin": "<500", "count": 2215}, {"bin": "500-2k", "count": 5480}, {"bin": "2k-10k", "count": 6112}, {"bin": ">10k", "count": 1193}], None),
    ("marketing_campaigns", "roi",          "numeric", 15000, 0, None,   "-0.46", "238056.83",194.37,    2642.17,   3.51,     15.96,    71.41,
     [{"bin": "<0", "count": 312}, {"bin": "0-10", "count": 4891}, {"bin": "10-100", "count": 6432}, {"bin": ">100", "count": 3365}], None),
    ("marketing_campaigns", "quality_score","numeric", 15000, 0, None,   "1.0",   "10.0",     5.48,      2.57,      3.2,      5.5,      7.8,
     [{"bin": "0-2", "count": 982}, {"bin": "2-5", "count": 4112}, {"bin": "5-8", "count": 7231}, {"bin": "8-10", "count": 2675}], None),
    ("marketing_campaigns", "channel",      "categorical", 15000, 0, 6,  None,    None,       None,      None,      None,     None,     None,
     None, [{"value": "social_media", "count": 4488}, {"value": "email", "count": 3745}, {"value": "search", "count": 3065}, {"value": "display", "count": 1483}, {"value": "influencer", "count": 1180}]),
    ("marketing_campaigns", "campaign_type","categorical", 15000, 0, 4,  None,    None,       None,      None,      None,     None,     None,
     None, [{"value": "acquisition", "count": 5871}, {"value": "retention", "count": 3840}, {"value": "awareness", "count": 3766}, {"value": "re_engagement", "count": 1523}]),

    # gigler_transactions
    ("gigler_transactions", "amount_usd",   "numeric", 20000, 0, None,   "0.01",  "47303.65", 323.99,    976.78,    65.62,    148.14,   340.86,
     [{"bin": "<50", "count": 2831}, {"bin": "50-200", "count": 8820}, {"bin": "200-1k", "count": 6441}, {"bin": ">1k", "count": 1908}], None),
    ("gigler_transactions", "rating",       "numeric", 20000, 0, None,   "1.0",   "5.0",      4.05,      0.68,      3.7,      4.2,      4.6,
     [{"bin": "1-2", "count": 312}, {"bin": "2-3", "count": 843}, {"bin": "3-4", "count": 4881}, {"bin": "4-5", "count": 13964}], None),
    ("gigler_transactions", "completion_days","numeric",20000,0, None,   "0",     "60",       9.51,      8.61,      3.0,      7.0,      14.0,
     [{"bin": "0-3", "count": 4210}, {"bin": "3-7", "count": 5891}, {"bin": "7-14", "count": 6320}, {"bin": ">14", "count": 3579}], None),
    ("gigler_transactions", "status",       "categorical", 20000, 0, 4,  None,    None,       None,      None,      None,     None,     None,
     None, [{"value": "completed", "count": 19025}, {"value": "cancelled", "count": 579}, {"value": "disputed", "count": 309}, {"value": "in_progress", "count": 87}]),
    ("gigler_transactions", "gig_category", "categorical", 20000, 0, 15, None,    None,       None,      None,      None,     None,     None,
     None, [{"value": "Social Media Management", "count": 1382}, {"value": "Financial Modeling", "count": 1370}, {"value": "Translation", "count": 1355}, {"value": "Photography", "count": 1350}, {"value": "SEO/SEM", "count": 1349}]),

    # gig_vendor_stats
    ("gig_vendor_stats", "avg_vendor_rating", "numeric", 6840, 0, None, "3.59", "4.84", 4.16, 0.25, 3.95, 4.14, 4.34,
     [{"bin": "3.5-4.0", "count": 1820}, {"bin": "4.0-4.5", "count": 3912}, {"bin": "4.5-5.0", "count": 1108}], None),
    ("gig_vendor_stats", "n_active_vendors", "numeric", 6840, 0, None,  "-5", "8808", 2858.98, 2134.5, 980.0, 2450.0, 4410.0,
     [{"bin": "<500", "count": 620}, {"bin": "500-2k", "count": 1940}, {"bin": "2k-5k", "count": 2891}, {"bin": ">5k", "count": 1389}], None),
    ("gig_vendor_stats", "click_through_rate","numeric", 6840, 0, None, "0.01", "0.89", 0.12, 0.08, 0.06, 0.11, 0.17,
     [{"bin": "0-0.05", "count": 812}, {"bin": "0.05-0.15", "count": 3421}, {"bin": "0.15-0.3", "count": 2190}, {"bin": ">0.3", "count": 417}], None),

    # gig_prices
    ("gig_prices", "avg_price_usd",    "numeric", 6840, 0, None, "29.92",  "10645.26", 318.59, 354.12, 120.94, 237.43, 470.04,
     [{"bin": "<100", "count": 1230}, {"bin": "100-300", "count": 2891}, {"bin": "300-1k", "count": 2108}, {"bin": ">1k", "count": 611}], None),
    ("gig_prices", "price_change_pct", "numeric", 6840, 0, None, "-15.2",  "28.4",     0.70,   4.81,   -1.8,   0.5,    3.1,
     [{"bin": "<-5", "count": 412}, {"bin": "-5-0", "count": 2180}, {"bin": "0-5", "count": 3291}, {"bin": ">5", "count": 957}], None),
]

def seed_profiles(cur):
    profile_time = days_ago(1)
    for (tname, col_name, dtg, row_count, null_count, distinct_count,
         min_val, max_val, mean_val, stddev_val, p25, p50, p75,
         histogram_bins, top_values) in PROFILES:
        cid = COLUMN_IDS.get(f"{tname}.{col_name}")
        if not cid:
            continue
        cur.execute("""
            INSERT INTO column_profiles (id, column_id, profiled_at, row_count, null_count,
                                         distinct_count, min_val, max_val, mean_val, stddev_val,
                                         p25, p50, p75, histogram_bins, top_values, data_type_group)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            uid(), cid, profile_time, row_count, null_count,
            distinct_count,
            str(min_val) if min_val is not None else None,
            str(max_val) if max_val is not None else None,
            mean_val, stddev_val, p25, p50, p75,
            json.dumps(histogram_bins) if histogram_bins else None,
            json.dumps(top_values) if top_values else None,
            dtg,
        ))
    print(f"  column profiles: {len(PROFILES)}")


# ---------------------------------------------------------------------------
# 6. Checks
# ---------------------------------------------------------------------------
CHECKS_SPEC: list[dict] = [
    # marketing_campaigns
    {"table": "marketing_campaigns", "col": "campaign_id",   "slug": "null_fraction",    "name": "campaign_id not null",               "params": {"threshold": 0.01}},
    {"table": "marketing_campaigns", "col": "date",          "slug": "null_fraction",    "name": "date not null",                      "params": {"threshold": 0.01}},
    {"table": "marketing_campaigns", "col": "channel",       "slug": "set_membership",   "name": "channel valid values",               "params": {"valid_set": ["social_media","email","search","display","influencer","video"]}},
    {"table": "marketing_campaigns", "col": "roi",           "slug": "value_in_range",   "name": "roi above -1",                       "params": {"min": -1.0}},
    {"table": "marketing_campaigns", "col": "quality_score", "slug": "value_in_range",   "name": "quality_score 0-10",                 "params": {"min": 0.0, "max": 10.0}},
    {"table": "marketing_campaigns", "col": None,            "slug": "volume",           "name": "campaign volume min 50",             "params": {"min": 50}},
    {"table": "marketing_campaigns", "col": "spend_usd",     "slug": "null_fraction",    "name": "spend_usd not null",                 "params": {"threshold": 0.01}},

    # gigler_transactions
    {"table": "gigler_transactions", "col": "transaction_id","slug": "null_fraction",    "name": "transaction_id not null",            "params": {"threshold": 0.0}},
    {"table": "gigler_transactions", "col": "amount_usd",    "slug": "null_fraction",    "name": "amount_usd not null",                "params": {"threshold": 0.01}},
    {"table": "gigler_transactions", "col": "amount_usd",    "slug": "value_in_range",   "name": "amount_usd positive",               "params": {"min": 0.0}},
    {"table": "gigler_transactions", "col": "rating",        "slug": "value_in_range",   "name": "rating 1-5",                        "params": {"min": 1.0, "max": 5.0}},
    {"table": "gigler_transactions", "col": "status",        "slug": "set_membership",   "name": "status valid values",               "params": {"valid_set": ["completed","cancelled","disputed","in_progress"]}},
    {"table": "gigler_transactions", "col": None,            "slug": "volume",           "name": "transaction volume min 100",        "params": {"min": 100}},
    {"table": "gigler_transactions", "col": "rating",        "slug": "numeric_mean",     "name": "avg rating above 3.5",             "params": {"min": 3.5}},

    # gig_vendor_stats
    {"table": "gig_vendor_stats",    "col": "date",               "slug": "null_fraction", "name": "date not null",                   "params": {"threshold": 0.0}},
    {"table": "gig_vendor_stats",    "col": "avg_vendor_rating",  "slug": "value_in_range","name": "avg_vendor_rating 1-5",          "params": {"min": 1.0, "max": 5.0}},
    {"table": "gig_vendor_stats",    "col": "click_through_rate", "slug": "value_in_range","name": "click_through_rate 0-1",         "params": {"min": 0.0, "max": 1.0}},

    # gig_prices
    {"table": "gig_prices",          "col": "date",               "slug": "null_fraction", "name": "date not null",                   "params": {"threshold": 0.0}},
    {"table": "gig_prices",          "col": "avg_price_usd",      "slug": "value_in_range","name": "avg_price_usd positive",         "params": {"min": 0.0}},
    {"table": "gig_prices",          "col": "gig_category",       "slug": "null_fraction", "name": "gig_category not null",          "params": {"threshold": 0.0}},
]

CHECK_IDS: dict[str, str] = {}  # check name -> uuid

def seed_checks(cur):
    for spec in CHECKS_SPEC:
        cid = uid()
        CHECK_IDS[spec["name"]] = cid
        col_id = COLUMN_IDS.get(f"{spec['table']}.{spec['col']}") if spec.get("col") else None
        dataset_id = DATASET_IDS[spec["table"]]
        cur.execute("""
            INSERT INTO checks (id, tenant_id, dataset_id, column_id, detector_slug, detector_params,
                                name, group_name, schedule, enabled, owner, tags, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            cid, TENANT_ID, dataset_id, col_id, spec["slug"],
            json.dumps(spec.get("params", {})),
            spec["name"], spec["slug"].split("_")[0], "0 */6 * * *", True,
            OWNER, [spec["table"]], days_ago(30), days_ago(1),
        ))
    print(f"  checks: {len(CHECK_IDS)}")


# ---------------------------------------------------------------------------
# 7. Check Runs + Incidents
# ---------------------------------------------------------------------------
# Scenario: most checks pass; 3 are failing right now to create incidents.
FAILING_CHECKS = {
    "avg rating above 3.5":    ("warn",  3.12, "Average rating dropped to 3.12, below threshold of 3.5. Observed over last 24h window."),
    "transaction volume min 100": ("fail", 0.0, "Row count dropped to 42 — well below minimum of 100. Possible data pipeline failure."),
    "campaign volume min 50":  ("warn",  0.0, "Only 31 campaigns loaded in last batch. Expected at least 50."),
}

BASELINE_IDS: dict[str, str] = {}
RUN_IDS: dict[str, str] = {}

def seed_check_runs_and_incidents(cur):
    for check_name, check_id in CHECK_IDS.items():
        is_failing = check_name in FAILING_CHECKS
        # Create 3 historical runs (passing) then the current run
        for i in range(3, 0, -1):
            run_id = uid()
            started = days_ago(i)
            finished = (dt.datetime.utcnow() - dt.timedelta(days=i) + dt.timedelta(seconds=2)).isoformat()
            cur.execute("""
                INSERT INTO check_runs (id, tenant_id, check_id, detector_slug, detector_version,
                                        started_at, finished_at, verdict, score, plain_english,
                                        details, triggered_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                run_id, TENANT_ID, check_id,
                next(s["slug"] for s in CHECKS_SPEC if s["name"] == check_name),
                "1", started, finished, "pass", 0.0,
                f"Check passed. No anomalies detected.", json.dumps({}), "schedule",
            ))

        # Current run
        run_id = uid()
        RUN_IDS[check_name] = run_id
        verdict = "fail" if is_failing and FAILING_CHECKS[check_name][0] == "fail" else \
                  "warn" if is_failing else "pass"
        score = FAILING_CHECKS[check_name][1] if is_failing else 0.0
        plain = FAILING_CHECKS[check_name][2] if is_failing else "Check passed."
        cur.execute("""
            INSERT INTO check_runs (id, tenant_id, check_id, detector_slug, detector_version,
                                    started_at, finished_at, verdict, score, plain_english,
                                    details, triggered_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            run_id, TENANT_ID, check_id,
            next(s["slug"] for s in CHECKS_SPEC if s["name"] == check_name),
            "1", days_ago(0), now(), verdict, score, plain,
            json.dumps({"threshold_violated": is_failing}), "schedule",
        ))

        if is_failing:
            severity = FAILING_CHECKS[check_name][0]
            title = f"{check_name} — {severity.upper()}"
            cur.execute("""
                INSERT INTO incidents (id, tenant_id, check_id, run_id, detector_slug,
                                       severity, status, title, opened_at, score, meta)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                uid(), TENANT_ID, check_id, run_id,
                next(s["slug"] for s in CHECKS_SPEC if s["name"] == check_name),
                severity, "open", title, days_ago(0), score,
                json.dumps({"auto_detected": True}),
            ))

    print(f"  check_runs: {len(CHECK_IDS) * 4} (3 historical + 1 current per check)")
    print(f"  incidents: {len(FAILING_CHECKS)} open")


# ---------------------------------------------------------------------------
# 8. Metrics
# ---------------------------------------------------------------------------
METRICS_SPEC = [
    {"slug": "daily_revenue",       "name": "Daily Revenue",          "kind": "sum",   "expr": "SUM(revenue_usd) FROM marketing_campaigns",    "unit": "USD",    "domain": "marketing",   "desc": "Total revenue attributed to marketing campaigns per day."},
    {"slug": "daily_transactions",  "name": "Daily Transactions",     "kind": "count", "expr": "COUNT(*) FROM gigler_transactions",             "unit": "count",  "domain": "marketplace", "desc": "Number of gig transactions completed per day."},
    {"slug": "avg_roi",             "name": "Campaign Avg ROI",       "kind": "ratio", "expr": "AVG(roi) FROM marketing_campaigns",             "unit": "%",      "domain": "marketing",   "desc": "Average return on investment across all active campaigns."},
    {"slug": "avg_rating",          "name": "Avg Transaction Rating", "kind": "ratio", "expr": "AVG(rating) FROM gigler_transactions",          "unit": "score",  "domain": "marketplace", "desc": "Average buyer satisfaction rating for completed gig transactions."},
    {"slug": "avg_transaction_value","name": "Avg Transaction Value", "kind": "ratio", "expr": "AVG(amount_usd) FROM gigler_transactions",      "unit": "USD",    "domain": "marketplace", "desc": "Mean transaction value in USD across all gig purchases."},
    {"slug": "cancellation_rate",   "name": "Cancellation Rate",      "kind": "ratio", "expr": "countIf(status='cancelled')/COUNT(*) FROM gigler_transactions", "unit": "%", "domain": "marketplace", "desc": "Fraction of transactions that were cancelled."},
    {"slug": "avg_gig_price",       "name": "Avg Gig Price",          "kind": "ratio", "expr": "AVG(avg_price_usd) FROM gig_prices",            "unit": "USD",    "domain": "marketplace", "desc": "Average listed price per gig across all categories."},
    {"slug": "campaign_spend",      "name": "Campaign Spend",         "kind": "sum",   "expr": "SUM(spend_usd) FROM marketing_campaigns",       "unit": "USD",    "domain": "marketing",   "desc": "Total marketing spend across all channels and campaign types."},
]

METRIC_IDS: dict[str, str] = {}

def seed_metrics(cur):
    for spec in METRICS_SPEC:
        mid = uid()
        METRIC_IDS[spec["slug"]] = mid
        yaml_def = f"""id: {spec['slug']}
name: {spec['name']}
kind: {spec['kind']}
source: "{spec['expr']}"
unit: {spec['unit']}
domain: {spec['domain']}
owner: {OWNER}
"""
        cur.execute("""
            INSERT INTO metrics (id, tenant_id, slug, name, kind, source_expr, description,
                                 unit, owner, domain, tags, yaml_definition, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (tenant_id, slug) DO UPDATE SET name=EXCLUDED.name, updated_at=now()
            RETURNING id
        """, (
            mid, TENANT_ID, spec["slug"], spec["name"], spec["kind"],
            spec["expr"], spec["desc"], spec["unit"], OWNER, spec["domain"],
            [spec["domain"]], yaml_def, days_ago(30), days_ago(1),
        ))
        row = cur.fetchone()
        if row:
            METRIC_IDS[spec["slug"]] = row["id"]
    print(f"  metrics: {len(METRIC_IDS)}")


# ---------------------------------------------------------------------------
# 9. Metric Runs (30 days of synthetic time series)
# ---------------------------------------------------------------------------
# Base values and daily noise (realistic ranges from real CH data)
METRIC_BASES = {
    "daily_revenue":        (52000,  8000),
    "daily_transactions":   (667,    80),
    "avg_roi":              (194,    40),
    "avg_rating":           (4.05,   0.15),
    "avg_transaction_value":(324,    30),
    "cancellation_rate":    (0.029,  0.005),
    "avg_gig_price":        (318,    20),
    "campaign_spend":       (3480,   500),
}

def seed_metric_runs(cur):
    inserts = []
    r = random.Random(42)
    for slug, (base, noise) in METRIC_BASES.items():
        mid = METRIC_IDS[slug]
        for day in range(30, 0, -1):
            # Simulate a slight downtrend in ratings and spike in cancellations in last 3 days
            trend_factor = 1.0
            if slug == "avg_rating" and day <= 3:
                trend_factor = 0.92  # rating drop
            if slug == "cancellation_rate" and day <= 3:
                trend_factor = 1.4  # cancellations spike
            val = base * trend_factor + r.gauss(0, noise)
            val = max(0, val)
            ts = days_ago(day)
            inserts.append((uid(), mid, TENANT_ID, ts, round(val, 4), json.dumps({})))
    cur.executemany("""
        INSERT INTO metric_runs (id, metric_id, tenant_id, measured_at, value, dimension_filters)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, inserts)
    print(f"  metric_runs: {len(inserts)}")


# ---------------------------------------------------------------------------
# 10. Causal Edges
# ---------------------------------------------------------------------------
CAUSAL_SPEC = [
    # (cause_slug, effect_slug, weight, e_value, stability, status, lag, method)
    ("campaign_spend",    "daily_revenue",       0.72, 3.8, 0.91, "confirmed", 0, "pcmci"),
    ("campaign_spend",    "avg_roi",             0.45, 2.1, 0.78, "confirmed", 1, "granger"),
    ("avg_gig_price",     "cancellation_rate",   0.38, 1.3, 0.62, "proposed",  2, "pcmci"),
    ("avg_gig_price",     "avg_transaction_value",0.65,2.9, 0.85, "confirmed", 0, "pcmci"),
    ("daily_transactions","avg_rating",          -0.28,1.7, 0.71, "confirmed", 1, "granger"),
]

def seed_causal_edges(cur):
    for (cause_slug, effect_slug, weight, e_value, stability, status, lag, method) in CAUSAL_SPEC:
        cause_id = METRIC_IDS.get(cause_slug)
        effect_id = METRIC_IDS.get(effect_slug)
        if not cause_id or not effect_id:
            continue
        confirmed_at = days_ago(5) if status == "confirmed" else None
        cur.execute("""
            INSERT INTO causal_edges (id, tenant_id, cause_metric_id, effect_metric_id,
                                      method, lag_periods, weight, e_value, stability_score,
                                      status, discovered_at, confirmed_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (tenant_id, cause_metric_id, effect_metric_id, method) DO UPDATE
            SET weight=EXCLUDED.weight, status=EXCLUDED.status, stability_score=EXCLUDED.stability_score
        """, (
            uid(), TENANT_ID, cause_id, effect_id,
            method, lag, weight, e_value, stability,
            status, days_ago(7), confirmed_at,
        ))
    print(f"  causal_edges: {len(CAUSAL_SPEC)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"Seeding database: {DATABASE_URL[:DATABASE_URL.index('@') + 1]}...")
    conn, cur = conn_cursor(DATABASE_URL)
    try:
        seed_tenant(cur)
        seed_source(cur)
        seed_datasets(cur)
        seed_columns(cur)
        seed_profiles(cur)
        seed_checks(cur)
        seed_check_runs_and_incidents(cur)
        seed_metrics(cur)
        seed_metric_runs(cur)
        seed_causal_edges(cur)
        conn.commit()
        print("\nDone — all data committed.")
    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        import traceback; traceback.print_exc()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

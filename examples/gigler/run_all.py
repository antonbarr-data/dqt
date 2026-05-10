#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gigler Demo -- End-to-End dqt Run
Demonstrates: data loading, profiling, DQ checks, causality analysis,
AI explanations, and HTML report generation.

Run:
    cd c:\\anton\\dqt
    uv run python examples/gigler/run_all.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Load .env before any imports that need it
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass  # python-dotenv optional; key can also be set as env var directly

# Repo root on sys.path (so dqt is importable without install)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT / "packages" / "dqt" / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "packages" / "dqt" / "src"))

import duckdb
import numpy as np
import pandas as pd

import dqt  # triggers all detector registrations via __init__.py
from dqt.adapters._protocol import AggExpr, ColumnMeta, HealthCheckResult, HealthCheckStep
from dqt.checks.models import Check
from dqt.profiling.profiler import DataProfiler
from dqt.reporting.html_report import profiling_report, quality_report, save_report, _md_to_html
from dqt.reporting._charts import time_series_chart
from dqt.runner.runner import Runner
from dqt.store.memory import MemoryStore

# Data dir relative to this script
_DATA_DIR = Path(__file__).parent / "data"
_OUTPUT_DIR = Path(__file__).parent / "reports"


# ---------------------------------------------------------------------------
# DemoAdapter
# ---------------------------------------------------------------------------

class DemoAdapter:
    """Minimal WarehouseAdapter backed by an in-memory DuckDB connection."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def sample(self, schema: str, table: str, n: int = 100_000, **kwargs) -> pd.DataFrame:
        return self._conn.execute(f"SELECT * FROM {table} LIMIT {n}").fetchdf()

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, object]:
        expr_sql = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        row = self._conn.execute(f"SELECT {expr_sql} FROM {table}").fetchone()
        if row is None:
            return {e.name: None for e in exprs}
        return {e.name: v for e, v in zip(exprs, row)}

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        rows = self._conn.execute(f"DESCRIBE {table}").fetchall()
        return [
            ColumnMeta(name=r[0], data_type=r[1], nullable=(r[2] == "YES"), position=i)
            for i, r in enumerate(rows)
        ]

    def list_schemas(self) -> list[str]:
        return ["main"]

    def list_tables(self, schema: str) -> list[str]:
        return [r[0] for r in self._conn.execute("SHOW TABLES").fetchall()]

    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(steps=[
            HealthCheckStep(name="tcp", status="pass", latency_ms=0.0, detail="in-memory"),
        ])


# ---------------------------------------------------------------------------
# Phase 1: Load data
# ---------------------------------------------------------------------------

def load_data() -> tuple[duckdb.DuckDBPyConnection, DemoAdapter]:
    conn = duckdb.connect(":memory:")
    mkt_glob    = str(_DATA_DIR / "marketing_campaigns_*.csv").replace("\\", "/")
    txn_glob    = str(_DATA_DIR / "gigler_transactions_*.csv").replace("\\", "/")
    price_glob  = str(_DATA_DIR / "gig_prices_*.csv").replace("\\", "/")
    vendor_glob = str(_DATA_DIR / "gig_vendor_stats_*.csv").replace("\\", "/")
    conn.execute(f"CREATE TABLE marketing       AS SELECT * FROM read_csv_auto('{mkt_glob}')")
    conn.execute(f"CREATE TABLE transactions    AS SELECT * FROM read_csv_auto('{txn_glob}')")
    conn.execute(f"CREATE TABLE gig_prices      AS SELECT * FROM read_csv_auto('{price_glob}')")
    conn.execute(f"CREATE TABLE gig_vendor_stats AS SELECT * FROM read_csv_auto('{vendor_glob}')")
    mkt_rows    = conn.execute("SELECT COUNT(*) FROM marketing").fetchone()[0]
    txn_rows    = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    price_rows  = conn.execute("SELECT COUNT(*) FROM gig_prices").fetchone()[0]
    vendor_rows = conn.execute("SELECT COUNT(*) FROM gig_vendor_stats").fetchone()[0]
    print(f"  Marketing:       {mkt_rows:,} rows")
    print(f"  Transactions:    {txn_rows:,} rows")
    print(f"  Gig prices:      {price_rows:,} rows")
    print(f"  Vendor stats:    {vendor_rows:,} rows")
    return conn, DemoAdapter(conn)


# ---------------------------------------------------------------------------
# Phase 2: Profile datasets
# ---------------------------------------------------------------------------

def profile_datasets(adapter: DemoAdapter):
    profiler = DataProfiler(adapter)
    marketing_profile = profiler.profile("main", "marketing",        sample_n=15_000)
    txn_profile       = profiler.profile("main", "transactions",     sample_n=20_000)
    price_profile     = profiler.profile("main", "gig_prices",       sample_n=10_000)
    vendor_profile    = profiler.profile("main", "gig_vendor_stats", sample_n=10_000)
    print(
        f"  Profiled {len(marketing_profile.columns)} marketing columns "
        f"({marketing_profile.row_count:,} sample rows)"
    )
    print(
        f"  Profiled {len(txn_profile.columns)} transaction columns "
        f"({txn_profile.row_count:,} sample rows)"
    )
    print(
        f"  Profiled {len(price_profile.columns)} gig_prices columns "
        f"({price_profile.row_count:,} sample rows)"
    )
    print(
        f"  Profiled {len(vendor_profile.columns)} gig_vendor_stats columns "
        f"({vendor_profile.row_count:,} sample rows)"
    )
    return marketing_profile, txn_profile, price_profile, vendor_profile


# ---------------------------------------------------------------------------
# Phase 3: Run DQ checks
# ---------------------------------------------------------------------------

def run_dq_checks(adapter: DemoAdapter) -> list[dict]:
    """Run DQ checks via the dqt Runner + registry.

    Aggregate detectors (completeness, uniqueness, null_fraction) use the
    adapter.aggregate() path -- the runner calls it with the right AggExprs.

    Sample detectors (mad_outlier_fraction, double_mad_outlier_fraction,
    adjusted_boxplot_fraction, zscore_outlier_fraction) use iloc[:, 0] on the
    DataFrame returned by adapter.sample(). The adapter must therefore return
    only the target column. We handle this by wrapping the adapter in a thin
    shim that selects the correct column before returning the sample.
    """
    from dqt.algorithms._registry import registry

    checks = [
        # -- Marketing dataset -------------------------------------------------
        # quality_score: 10-15% NULL is expected (platform collection failures)
        Check(schema_name="main", table_name="marketing", column_name="quality_score",
              detector_slug="null_fraction"),
        # campaign_id completeness -- should be 100%
        Check(schema_name="main", table_name="marketing", column_name="campaign_id",
              detector_slug="completeness"),
        # campaign_id uniqueness -- MC-NNNNN+date composite, so <100% is fine
        Check(schema_name="main", table_name="marketing", column_name="campaign_id",
              detector_slug="uniqueness"),
        # spend_usd outliers: modified Z-score (MAD) -- suitable for the roughly
        # log-normal distribution; spikes >$5k/day are flagged
        Check(schema_name="main", table_name="marketing", column_name="spend_usd",
              detector_slug="mad_outlier_fraction"),
        # impressions outliers: adjusted boxplot with medcouple correction --
        # robust on the positively-skewed impression distribution
        Check(schema_name="main", table_name="marketing", column_name="impressions",
              detector_slug="adjusted_boxplot_fraction"),
        # roi outliers: plain Z-score is acceptable; ROI is approximately symmetric
        Check(schema_name="main", table_name="marketing", column_name="roi",
              detector_slug="zscore_outlier_fraction"),

        # -- Gig prices dataset ------------------------------------------------
        # avg_price_usd null fraction: 0.5% data collection failures expected
        Check(schema_name="main", table_name="gig_prices", column_name="avg_price_usd",
              detector_slug="null_fraction"),
        # avg_price_usd outliers: MAD catches the injected 10× price spikes
        Check(schema_name="main", table_name="gig_prices", column_name="avg_price_usd",
              detector_slug="mad_outlier_fraction"),
        # gig_category completeness: every row must have a category
        Check(schema_name="main", table_name="gig_prices", column_name="gig_category",
              detector_slug="completeness"),

        # -- Vendor competition dataset ----------------------------------------
        # total_profile_views: 0.2% NULL expected (tracking pixel outages)
        Check(schema_name="main", table_name="gig_vendor_stats", column_name="total_profile_views",
              detector_slug="null_fraction"),
        # search_impressions: 0.3% NULL expected (search indexer failures)
        Check(schema_name="main", table_name="gig_vendor_stats", column_name="search_impressions",
              detector_slug="null_fraction"),
        # n_active_vendors completeness: pipeline errors produce 0.4% zeros/negatives
        Check(schema_name="main", table_name="gig_vendor_stats", column_name="n_active_vendors",
              detector_slug="completeness"),
        # total_profile_views outliers: MAD catches spikes from viral promotions
        Check(schema_name="main", table_name="gig_vendor_stats", column_name="total_profile_views",
              detector_slug="mad_outlier_fraction"),
        # click_through_rate: adjusted boxplot catches the injected > 1.0 tracking bugs
        Check(schema_name="main", table_name="gig_vendor_stats", column_name="click_through_rate",
              detector_slug="adjusted_boxplot_fraction"),

        # -- Transactions dataset -----------------------------------------------
        # amount_usd: double-MAD for asymmetric, skewed payment amounts
        Check(schema_name="main", table_name="transactions", column_name="amount_usd",
              detector_slug="double_mad_outlier_fraction"),
        # completion_days: adjusted boxplot -- right-skewed delivery time distribution
        Check(schema_name="main", table_name="transactions", column_name="completion_days",
              detector_slug="adjusted_boxplot_fraction"),
        # rating: MAD to catch the cluster at 1.0 (service quality signal)
        Check(schema_name="main", table_name="transactions", column_name="rating",
              detector_slug="mad_outlier_fraction"),
        # rating null fraction: NULL if transaction not yet completed
        Check(schema_name="main", table_name="transactions", column_name="rating",
              detector_slug="null_fraction"),
        # transaction_id should be globally unique
        Check(schema_name="main", table_name="transactions", column_name="transaction_id",
              detector_slug="uniqueness"),
        # amount_usd completeness -- must be 100%
        Check(schema_name="main", table_name="transactions", column_name="amount_usd",
              detector_slug="completeness"),
    ]

    store = MemoryStore()
    dq_results: list[dict] = []

    _ICON = {"pass": "[PASS]", "warn": "[WARN]", "fail": "[FAIL]"}

    for check in checks:
        try:
            cls = registry.get(check.detector_slug)
            detector = cls(**(check.params or {}))

            if detector.kind == "aggregate":
                # Aggregate detectors: the runner's aggregate path works correctly
                runner = Runner(store)
                runner.fit(check, adapter)
                result = runner.run(check, adapter)
            else:
                # Sample detectors: fetch only the target column so that
                # iloc[:, 0] inside the detector picks up the right values.
                col_name = check.column_name
                full_df = adapter.sample(check.schema_name, check.table_name, check.sample_n)
                col_df = full_df[[col_name]]  # single-column DataFrame

                state = detector.fit(col_df)
                det_result = detector.score(col_df, state)
                result = det_result  # DetectorResult, not RunResult; handled below

        except Exception as exc:
            print(
                f"  [ERR]  {check.table_name}.{check.column_name} "
                f"[{check.detector_slug}] ERROR: {exc}"
            )
            dq_results.append({
                "check": check.detector_slug,
                "table": check.table_name,
                "column": check.column_name or "",
                "verdict": "error",
                "score": 0.0,
                "plain_english": str(exc),
            })
            continue

        # Normalise RunResult vs DetectorResult into the same dict shape
        verdict_val = result.verdict.value if hasattr(result.verdict, "value") else str(result.verdict)
        icon = _ICON.get(verdict_val, "[?]")
        # Encode plain_english to ASCII, replacing non-ASCII chars, for Windows consoles
        safe_msg = result.plain_english[:90].encode("ascii", errors="replace").decode("ascii")
        print(
            f"  {icon}  {check.table_name}.{check.column_name} "
            f"[{check.detector_slug}]  score={result.score:.4f} -- "
            f"{safe_msg}"
        )
        # Build diagnostic_sql: RunResult has it directly; for DetectorResult construct from failing_filter_sql
        diag_sql: str | None = getattr(result, "diagnostic_sql", None)
        if diag_sql is None:
            failing_filter = getattr(result, "failing_filter_sql", None)
            if failing_filter and verdict_val in ("warn", "fail"):
                fq = f"{check.schema_name}.{check.table_name}"
                diag_sql = f"SELECT * FROM {fq}\nWHERE {failing_filter}\nLIMIT 20;"
        dq_results.append({
            "check": check.detector_slug,
            "table": check.table_name,
            "column": check.column_name or "",
            "verdict": verdict_val,
            "score": result.score,
            "plain_english": result.plain_english,
            "diagnostic_sql": diag_sql,
        })

    return dq_results


# ---------------------------------------------------------------------------
# Phase 4: Causality analysis
# ---------------------------------------------------------------------------

def run_causality(conn: duckdb.DuckDBPyConnection) -> tuple[dict, pd.DataFrame]:
    marketing_weekly = conn.execute("""
        SELECT
            DATE_TRUNC('week', CAST(date AS DATE))            AS week,
            SUM(CASE WHEN campaign_type = 'acquisition'
                     THEN spend_usd ELSE 0 END)               AS acquisition_spend,
            SUM(impressions)                                   AS total_impressions,
            SUM(conversions)                                   AS total_conversions
        FROM marketing
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()

    txn_weekly = conn.execute("""
        SELECT
            DATE_TRUNC('week', CAST(date AS DATE))  AS week,
            COUNT(*)                                AS transaction_count,
            SUM(amount_usd)                         AS total_revenue
        FROM transactions
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()

    price_weekly = conn.execute("""
        SELECT
            DATE_TRUNC('week', CAST(date AS DATE))  AS week,
            AVG(avg_price_usd)                      AS avg_gig_price
        FROM gig_prices
        WHERE avg_price_usd IS NOT NULL
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()

    vendor_weekly = conn.execute("""
        SELECT
            DATE_TRUNC('week', CAST(date AS DATE))              AS week,
            SUM(CASE WHEN n_active_vendors > 0
                     THEN n_active_vendors ELSE 0 END)          AS total_vendors,
            SUM(COALESCE(total_profile_views, 0))               AS total_profile_views,
            AVG(avg_vendor_rating)                              AS avg_vendor_rating
        FROM gig_vendor_stats
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()

    weekly = (
        marketing_weekly
        .merge(txn_weekly,    on="week", how="inner")
        .merge(price_weekly,  on="week", how="inner")
        .merge(vendor_weekly, on="week", how="inner")
        .sort_values("week")
        .reset_index(drop=True)
    )

    spend        = weekly["acquisition_spend"].values.astype(float)
    txn_vol      = weekly["transaction_count"].values.astype(float)
    price        = weekly["avg_gig_price"].values.astype(float)
    vendors      = weekly["total_vendors"].values.astype(float)
    views        = weekly["total_profile_views"].values.astype(float)

    # Spend → volume (positive, 2-week lag)
    lag0_corr = float(np.corrcoef(spend, txn_vol)[0, 1])
    lag1_corr = float(np.corrcoef(spend[:-1], txn_vol[1:])[0, 1])
    lag2_corr = float(np.corrcoef(spend[:-2], txn_vol[2:])[0, 1])

    # Price → volume (negative, 1-week lag)
    price_lag0_corr = float(np.corrcoef(price, txn_vol)[0, 1])
    price_lag1_corr = float(np.corrcoef(price[:-1], txn_vol[1:])[0, 1])
    price_lag2_corr = float(np.corrcoef(price[:-2], txn_vol[2:])[0, 1])

    # Vendor count → price (negative, 1-week lag): competition suppresses prices
    vc_lag0_corr = float(np.corrcoef(vendors, price)[0, 1])
    vc_lag1_corr = float(np.corrcoef(vendors[:-1], price[1:])[0, 1])
    vc_lag2_corr = float(np.corrcoef(vendors[:-2], price[2:])[0, 1])

    # Profile views → volume (positive, 1-week lag): eyeballs convert to purchases
    vw_lag0_corr = float(np.corrcoef(views, txn_vol)[0, 1])
    vw_lag1_corr = float(np.corrcoef(views[:-1], txn_vol[1:])[0, 1])
    vw_lag2_corr = float(np.corrcoef(views[:-2], txn_vol[2:])[0, 1])

    print(f"  Spend   -> volume  lag-0={lag0_corr:+.3f}  lag-1={lag1_corr:+.3f}  lag-2={lag2_corr:+.3f}  <- peak expected at 2w")
    print(f"  Price   -> volume  lag-0={price_lag0_corr:+.3f}  lag-1={price_lag1_corr:+.3f}  lag-2={price_lag2_corr:+.3f}  <- peak expected at 1w (negative)")
    print(f"  Vendors -> price   lag-0={vc_lag0_corr:+.3f}  lag-1={vc_lag1_corr:+.3f}  lag-2={vc_lag2_corr:+.3f}  <- peak expected at 1w (negative)")
    print(f"  Views   -> volume  lag-0={vw_lag0_corr:+.3f}  lag-1={vw_lag1_corr:+.3f}  lag-2={vw_lag2_corr:+.3f}  <- peak expected at 1w (positive)")

    lags = [(abs(lag0_corr), 0, lag0_corr), (abs(lag1_corr), 1, lag1_corr), (abs(lag2_corr), 2, lag2_corr)]
    peak_lag = max(lags)[1]

    if lag2_corr > lag1_corr and lag2_corr > lag0_corr:
        spend_conclusion = (
            f"Marketing acquisition spend Granger-causes transaction volume with a "
            f"2-week lag (r={lag2_corr:.3f}). Same-week correlation is weaker "
            f"(r={lag0_corr:.3f}), consistent with delayed conversion attribution."
        )
    else:
        spend_conclusion = (
            f"Peak spend correlation at lag-{peak_lag} week(s). "
            "No clear 2-week causal structure detected; check seasonal confounders."
        )

    if price_lag1_corr < price_lag0_corr and price_lag1_corr < price_lag2_corr:
        price_conclusion = (
            f"Average gig price negatively causes transaction volume with a 1-week lag "
            f"(r={price_lag1_corr:.3f}). Lower prices drive buyer demand — the effect "
            f"peaks one week after a price change, consistent with search-to-purchase latency."
        )
    else:
        price_conclusion = (
            f"Price-to-volume correlation: lag-0={price_lag0_corr:.3f}, "
            f"lag-1={price_lag1_corr:.3f}, lag-2={price_lag2_corr:.3f}."
        )

    if vc_lag1_corr < vc_lag0_corr and vc_lag1_corr < vc_lag2_corr:
        vendor_conclusion = (
            f"Total active vendor count negatively causes avg gig price with a 1-week lag "
            f"(r={vc_lag1_corr:.3f}). Competition from more vendors suppresses prices — "
            f"this is the upstream driver in the chain: vendors → price → transactions."
        )
    else:
        vendor_conclusion = (
            f"Vendor count-to-price correlation: lag-0={vc_lag0_corr:.3f}, "
            f"lag-1={vc_lag1_corr:.3f}, lag-2={vc_lag2_corr:.3f}."
        )

    if vw_lag1_corr > vw_lag0_corr and vw_lag1_corr > vw_lag2_corr:
        views_conclusion = (
            f"Total buyer profile views positively cause transaction volume with a 1-week lag "
            f"(r={vw_lag1_corr:.3f}). The eyeball-to-purchase funnel: browsing activity this "
            f"week predicts orders next week, independent of price or spend effects."
        )
    else:
        views_conclusion = (
            f"Profile views-to-volume correlation: lag-0={vw_lag0_corr:.3f}, "
            f"lag-1={vw_lag1_corr:.3f}, lag-2={vw_lag2_corr:.3f}."
        )

    causality_result = {
        "lag0_corr": lag0_corr,
        "lag1_corr": lag1_corr,
        "lag2_corr": lag2_corr,
        "peak_lag": peak_lag,
        "conclusion": spend_conclusion,
        "price_lag0_corr": price_lag0_corr,
        "price_lag1_corr": price_lag1_corr,
        "price_lag2_corr": price_lag2_corr,
        "price_conclusion": price_conclusion,
        "vc_lag0_corr": vc_lag0_corr,
        "vc_lag1_corr": vc_lag1_corr,
        "vc_lag2_corr": vc_lag2_corr,
        "vendor_conclusion": vendor_conclusion,
        "vw_lag0_corr": vw_lag0_corr,
        "vw_lag1_corr": vw_lag1_corr,
        "vw_lag2_corr": vw_lag2_corr,
        "views_conclusion": views_conclusion,
        "n_weeks": len(weekly),
        "weekly_data": weekly.to_dict(orient="records"),
    }
    return causality_result, weekly


# ---------------------------------------------------------------------------
# Phase 5: AI explanations via Claude API
# ---------------------------------------------------------------------------

def generate_explanations(
    dq_results: list[dict],
    causality_result: dict,
) -> tuple[str, str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        placeholder = "[ANTHROPIC_API_KEY not set -- AI explanation skipped]"
        return placeholder, placeholder

    try:
        import anthropic
    except ImportError:
        placeholder = "[anthropic package not installed -- AI explanation skipped]"
        return placeholder, placeholder

    client = anthropic.Anthropic(api_key=api_key)

    def _call(prompt: str, max_tokens: int = 600) -> str:
        try:
            msg = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as exc:
            return f"[AI explanation unavailable: {exc}]"

    # DQ summary -- warn/fail findings only
    bad_checks = [r for r in dq_results if r["verdict"] in ("warn", "fail", "error")]
    if bad_checks:
        dq_lines = "\n".join(
            f"- {r['table']}.{r['column']} [{r['check']}]: "
            f"{r['verdict'].upper()} -- {r['plain_english']}"
            for r in bad_checks
        )
    else:
        dq_lines = "All checks passed."

    dq_prompt = (
        "You are a data quality analyst for Gigler, a global freelance marketplace.\n\n"
        "Data quality scan results (warnings and failures only):\n"
        f"{dq_lines}\n\n"
        "Write a concise executive summary (4-6 sentences) covering:\n"
        "1. The most critical data quality issues found.\n"
        "2. Their potential business impact on Gigler operations.\n"
        "3. Recommended immediate actions.\n\n"
        "Be specific and business-focused. Avoid technical detector names."
    )

    print("  Calling Claude for DQ summary...", end=" ", flush=True)
    dq_ai = _call(dq_prompt)
    print("done")

    # Causality explanation
    causality_prompt = (
        "You are a data analyst at Gigler, a global freelance marketplace.\n\n"
        "Four causal signals in the data were discovered (full chain):\n\n"
        "1. Active vendor count → avg gig price (1-week lag, negative: competition suppresses prices):\n"
        f"   lag-0={causality_result['vc_lag0_corr']:+.3f}, "
        f"lag-1={causality_result['vc_lag1_corr']:+.3f}, "
        f"lag-2={causality_result['vc_lag2_corr']:+.3f}\n"
        f"   {causality_result['vendor_conclusion']}\n\n"
        "2. Avg gig price → transaction volume (1-week lag, negative: lower price = more orders):\n"
        f"   lag-0={causality_result['price_lag0_corr']:+.3f}, "
        f"lag-1={causality_result['price_lag1_corr']:+.3f}, "
        f"lag-2={causality_result['price_lag2_corr']:+.3f}\n"
        f"   {causality_result['price_conclusion']}\n\n"
        "3. Buyer profile views → transaction volume (1-week lag, positive: eyeballs convert):\n"
        f"   lag-0={causality_result['vw_lag0_corr']:+.3f}, "
        f"lag-1={causality_result['vw_lag1_corr']:+.3f}, "
        f"lag-2={causality_result['vw_lag2_corr']:+.3f}\n"
        f"   {causality_result['views_conclusion']}\n\n"
        "4. Acquisition spend → transaction volume (2-week lag, positive):\n"
        f"   lag-0={causality_result['lag0_corr']:+.3f}, "
        f"lag-1={causality_result['lag1_corr']:+.3f}, "
        f"lag-2={causality_result['lag2_corr']:+.3f}\n"
        f"   {causality_result['conclusion']}\n\n"
        f"Weeks analysed: {causality_result['n_weeks']}\n\n"
        "Write a concise business explanation (5-7 sentences) covering:\n"
        "1. The full causal chain: vendor competition → prices → transactions.\n"
        "2. The independent eyeball funnel: profile views → transactions.\n"
        "3. How the 2-week spend window complements the 1-week price/views signals.\n"
        "4. How to use all four signals together for short-term transaction forecasting.\n\n"
        "Be specific about lag structures and business levers."
    )

    print("  Calling Claude for causality explanation...", end=" ", flush=True)
    causality_ai = _call(causality_prompt)
    print("done")

    return dq_ai, causality_ai


# ---------------------------------------------------------------------------
# Causality report builder
# ---------------------------------------------------------------------------

def _build_causality_report(
    causality_result: dict,
    weekly_chart: str,
    txn_chart: str,
    price_chart: str,
    vendor_chart: str,
    views_chart: str,
    ai_explanation: str,
) -> str:
    lag0  = causality_result["lag0_corr"]
    lag1  = causality_result["lag1_corr"]
    lag2  = causality_result["lag2_corr"]
    pl0   = causality_result["price_lag0_corr"]
    pl1   = causality_result["price_lag1_corr"]
    pl2   = causality_result["price_lag2_corr"]
    vc0   = causality_result["vc_lag0_corr"]
    vc1   = causality_result["vc_lag1_corr"]
    vc2   = causality_result["vc_lag2_corr"]
    vw0   = causality_result["vw_lag0_corr"]
    vw1   = causality_result["vw_lag1_corr"]
    vw2   = causality_result["vw_lag2_corr"]
    conclusion        = causality_result["conclusion"]
    price_conclusion  = causality_result["price_conclusion"]
    vendor_conclusion = causality_result["vendor_conclusion"]
    views_conclusion  = causality_result["views_conclusion"]
    n_weeks = causality_result["n_weeks"]

    def _corr_color(v: float) -> str:
        if abs(v) > 0.5:
            return "#7FB394"
        if abs(v) > 0.3:
            return "#D9B566"
        return "#666E82"

    import html as _html
    safe_ai               = _md_to_html(ai_explanation)
    safe_conclusion       = _html.escape(conclusion)
    safe_price_conclusion = _html.escape(price_conclusion)
    safe_vendor_conclusion = _html.escape(vendor_conclusion)
    safe_views_conclusion  = _html.escape(views_conclusion)

    return (
        '<!DOCTYPE html>\n'
        '<html data-theme="dark">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<title>Gigler Causality Report</title>\n'
        '<style>\n'
        '*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n'
        'html, body {\n'
        '  background: #0F1117; color: #E8EAF0;\n'
        '  font-family: Inter, system-ui, sans-serif;\n'
        '  font-size: 13px; line-height: 1.5;\n'
        '  padding: 24px 48px;\n'
        '}\n'
        'h1 { font-size: 20px; font-weight: 300; letter-spacing: -0.02em; color: #9DD0B0; margin-bottom: 6px; }\n'
        'h2 { font-size: 14px; font-weight: 500; color: #E8EAF0; margin-bottom: 12px; }\n'
        'h3 { font-size: 12px; font-weight: 500; color: #9DD0B0; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.08em; }\n'
        '.brand { font-family: "JetBrains Mono", monospace; font-weight: 300; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #9DD0B0; margin-bottom: 8px; }\n'
        '.subtitle { color: #666E82; font-size: 12px; margin-bottom: 24px; }\n'
        '.section { background: #161B25; border: 1px solid #2A3147; padding: 20px 24px; margin-bottom: 16px; }\n'
        '.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }\n'
        '.chain-label { font-family: "JetBrains Mono", monospace; font-size: 11px; color: #666E82; margin-bottom: 12px; }\n'
        '.metric-row { display: flex; gap: 32px; margin: 8px 0 16px; }\n'
        '.metric { text-align: center; }\n'
        '.metric-val { font-family: "JetBrains Mono", monospace; font-size: 2rem; font-weight: 300; }\n'
        '.metric-label { color: #666E82; font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; font-family: "JetBrains Mono", monospace; }\n'
        '.conclusion { color: #A0A8B8; font-size: 12px; margin-top: 8px; line-height: 1.6; }\n'
        '.ai-box { background: #1A2E24; border-left: 3px solid #9DD0B0; padding: 16px 20px; color: #E8EAF0; line-height: 1.7; font-size: 12px; }\n'
        '.ai-box h2 { font-size: 13px; font-weight: 600; color: #9DD0B0; margin: 12px 0 4px; }\n'
        '.ai-box h3 { font-size: 12px; font-weight: 600; color: #A0A8B8; margin: 10px 0 4px; text-transform: none; letter-spacing: 0; }\n'
        '.ai-box p { margin: 4px 0; }\n'
        '.ai-box ul { margin: 4px 0 4px 20px; }\n'
        '.ai-box li { margin: 2px 0; }\n'
        'img { max-width: 100%; display: block; margin-top: 8px; }\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<div class="brand">dqt</div>\n'
        '<h1>Causality Analysis: Four Drivers of Transaction Volume</h1>\n'
        f'<p class="subtitle">Lag-correlation analysis &middot; {n_weeks} weeks &middot; '
        'full chain: vendors &#8594; price &#8594; volume + views &#8594; volume + spend &#8594; volume</p>\n'
        '\n'
        '<div class="section">\n'
        '<p class="chain-label">Competition chain: n_active_vendors &#8594; avg_price_usd &#8594; transaction_count</p>\n'
        '<div class="two-col">\n'
        '  <div>\n'
        '    <h3>Vendor Count &#8594; Gig Price (negative)</h3>\n'
        '    <div class="metric-row">\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(vc0)}">{vc0:+.3f}</div><div class="metric-label">lag 0w</div></div>\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(vc1)}">{vc1:+.3f}</div><div class="metric-label">lag 1w &#9650;</div></div>\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(vc2)}">{vc2:+.3f}</div><div class="metric-label">lag 2w</div></div>\n'
        '    </div>\n'
        f'    <p class="conclusion">{safe_vendor_conclusion}</p>\n'
        '  </div>\n'
        '  <div>\n'
        '    <h3>Avg Gig Price &#8594; Volume (negative)</h3>\n'
        '    <div class="metric-row">\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(pl0)}">{pl0:+.3f}</div><div class="metric-label">lag 0w</div></div>\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(pl1)}">{pl1:+.3f}</div><div class="metric-label">lag 1w &#9650;</div></div>\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(pl2)}">{pl2:+.3f}</div><div class="metric-label">lag 2w</div></div>\n'
        '    </div>\n'
        f'    <p class="conclusion">{safe_price_conclusion}</p>\n'
        '  </div>\n'
        '</div>\n'
        '</div>\n'
        '\n'
        '<div class="section">\n'
        '<p class="chain-label">Eyeball funnel: total_profile_views &#8594; transaction_count &nbsp;&nbsp;&nbsp; Marketing channel: acquisition_spend &#8594; transaction_count</p>\n'
        '<div class="two-col">\n'
        '  <div>\n'
        '    <h3>Profile Views &#8594; Volume (positive)</h3>\n'
        '    <div class="metric-row">\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(vw0)}">{vw0:+.3f}</div><div class="metric-label">lag 0w</div></div>\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(vw1)}">{vw1:+.3f}</div><div class="metric-label">lag 1w &#9650;</div></div>\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(vw2)}">{vw2:+.3f}</div><div class="metric-label">lag 2w</div></div>\n'
        '    </div>\n'
        f'    <p class="conclusion">{safe_views_conclusion}</p>\n'
        '  </div>\n'
        '  <div>\n'
        '    <h3>Acquisition Spend &#8594; Volume</h3>\n'
        '    <div class="metric-row">\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(lag0)}">{lag0:+.3f}</div><div class="metric-label">lag 0w</div></div>\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(lag1)}">{lag1:+.3f}</div><div class="metric-label">lag 1w</div></div>\n'
        f'      <div class="metric"><div class="metric-val" style="color:{_corr_color(lag2)}">{lag2:+.3f}</div><div class="metric-label">lag 2w &#9650;</div></div>\n'
        '    </div>\n'
        f'    <p class="conclusion">{safe_conclusion}</p>\n'
        '  </div>\n'
        '</div>\n'
        '</div>\n'
        '\n'
        '<div class="section">\n'
        '<h2>Weekly Active Vendor Count</h2>\n'
        f'<img src="data:image/png;base64,{vendor_chart}" alt="Weekly vendor count">\n'
        '</div>\n'
        '\n'
        '<div class="section">\n'
        '<h2>Weekly Avg Gig Price (USD)</h2>\n'
        f'<img src="data:image/png;base64,{price_chart}" alt="Weekly avg gig price">\n'
        '</div>\n'
        '\n'
        '<div class="section">\n'
        '<h2>Weekly Profile Views</h2>\n'
        f'<img src="data:image/png;base64,{views_chart}" alt="Weekly profile views">\n'
        '</div>\n'
        '\n'
        '<div class="section">\n'
        '<h2>Weekly Acquisition Spend (USD)</h2>\n'
        f'<img src="data:image/png;base64,{weekly_chart}" alt="Weekly acquisition spend">\n'
        '</div>\n'
        '\n'
        '<div class="section">\n'
        '<h2>Weekly Transaction Volume</h2>\n'
        f'<img src="data:image/png;base64,{txn_chart}" alt="Weekly transaction volume">\n'
        '</div>\n'
        '\n'
        '<div class="section">\n'
        '<h2>AI Interpretation</h2>\n'
        f'<div class="ai-box">{safe_ai}</div>\n'
        '</div>\n'
        '</body>\n'
        '</html>'
    )


# ---------------------------------------------------------------------------
# Phase 6: Generate HTML reports
# ---------------------------------------------------------------------------

def generate_reports(
    marketing_profile,
    txn_profile,
    price_profile,
    vendor_profile,
    dq_results: list[dict],
    causality_result: dict,
    weekly: pd.DataFrame,
    dq_ai: str,
    causality_ai: str,
) -> None:
    _OUTPUT_DIR.mkdir(exist_ok=True)

    # Marketing profiling report
    mkt_html = profiling_report(
        marketing_profile,
        title="Gigler Marketing Campaigns -- Data Profile",
        ai_summary=dq_ai,
    )
    save_report(mkt_html, str(_OUTPUT_DIR / "marketing_profile.html"))
    print(f"  Saved: {_OUTPUT_DIR / 'marketing_profile.html'}")

    # Transactions profiling report
    txn_html = profiling_report(
        txn_profile,
        title="Gigler Transactions -- Data Profile",
        ai_summary="",
    )
    save_report(txn_html, str(_OUTPUT_DIR / "transactions_profile.html"))
    print(f"  Saved: {_OUTPUT_DIR / 'transactions_profile.html'}")

    # Gig prices profiling report
    price_html = profiling_report(
        price_profile,
        title="Gigler Gig Prices -- Data Profile",
        ai_summary="",
    )
    save_report(price_html, str(_OUTPUT_DIR / "gig_prices_profile.html"))
    print(f"  Saved: {_OUTPUT_DIR / 'gig_prices_profile.html'}")

    # Vendor competition profiling report
    vendor_html = profiling_report(
        vendor_profile,
        title="Gigler Vendor Competition -- Data Profile",
        ai_summary="",
    )
    save_report(vendor_html, str(_OUTPUT_DIR / "vendor_stats_profile.html"))
    print(f"  Saved: {_OUTPUT_DIR / 'vendor_stats_profile.html'}")

    # DQ checks report
    dq_html = quality_report(
        dq_results,
        dataset_name="Gigler (Marketing + Transactions + Gig Prices + Vendor Stats)",
        title="Gigler Data Quality Report",
        ai_summary=dq_ai,
    )
    save_report(dq_html, str(_OUTPUT_DIR / "dq_report.html"))
    print(f"  Saved: {_OUTPUT_DIR / 'dq_report.html'}")

    # Causality report with time series charts
    weeks = [str(r["week"])[:10] for r in causality_result["weekly_data"]]
    weekly_chart = time_series_chart(
        dates=weeks,
        values=[float(r["acquisition_spend"]) for r in causality_result["weekly_data"]],
        title="Weekly Acquisition Spend",
        color="#9DD0B0",
    )
    price_chart = time_series_chart(
        dates=weeks,
        values=[float(r["avg_gig_price"]) for r in causality_result["weekly_data"]],
        title="Weekly Avg Gig Price (USD)",
        color="#D9B566",
    )
    txn_chart = time_series_chart(
        dates=weeks,
        values=[float(r["transaction_count"]) for r in causality_result["weekly_data"]],
        title="Weekly Transaction Volume",
        color="#E07B6E",
    )
    vendor_chart = time_series_chart(
        dates=weeks,
        values=[float(r["total_vendors"]) for r in causality_result["weekly_data"]],
        title="Weekly Active Vendor Count",
        color="#B08FE8",
    )
    views_chart = time_series_chart(
        dates=weeks,
        values=[float(r["total_profile_views"]) for r in causality_result["weekly_data"]],
        title="Weekly Profile Views",
        color="#6AAECC",
    )

    causality_html = _build_causality_report(
        causality_result=causality_result,
        weekly_chart=weekly_chart,
        txn_chart=txn_chart,
        price_chart=price_chart,
        vendor_chart=vendor_chart,
        views_chart=views_chart,
        ai_explanation=causality_ai,
    )
    save_report(causality_html, str(_OUTPUT_DIR / "causality_report.html"))
    print(f"  Saved: {_OUTPUT_DIR / 'causality_report.html'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 64)
    print("dqt -- Gigler End-to-End Demo")
    print("=" * 64)

    print("\n[Phase 0] Generating knowledge graph vault...")
    import subprocess
    subprocess.run([sys.executable, Path(__file__).parent / "generate_vault.py"], check=True)
    print("  Vault: examples/gigler/vault/")

    print("\n[Phase 1] Loading data...")
    conn, adapter = load_data()

    print("\n[Phase 2] Profiling datasets...")
    marketing_profile, txn_profile, price_profile, vendor_profile = profile_datasets(adapter)

    print("\n[Phase 3] Running DQ checks...")
    dq_results = run_dq_checks(adapter)

    print("\n[Phase 4] Causality analysis (full chain)...")
    causality_result, weekly = run_causality(conn)

    print("\n[Phase 5] Generating AI explanations via Claude API...")
    dq_ai, causality_ai = generate_explanations(dq_results, causality_result)

    print("\n[Phase 6] Generating HTML reports...")
    generate_reports(
        marketing_profile, txn_profile, price_profile, vendor_profile,
        dq_results, causality_result, weekly,
        dq_ai, causality_ai,
    )

    # Summary
    n_pass = sum(1 for r in dq_results if r["verdict"] == "pass")
    n_warn = sum(1 for r in dq_results if r["verdict"] == "warn")
    n_fail = sum(1 for r in dq_results if r["verdict"] == "fail")
    n_err  = sum(1 for r in dq_results if r["verdict"] == "error")

    print(f"\n{'=' * 64}")
    print(
        f"DQ Results:  {n_pass} pass  /  {n_warn} warn  /  "
        f"{n_fail} fail  /  {n_err} error"
    )
    print(
        f"Causality:   lag-0={causality_result['lag0_corr']:+.3f}  "
        f"lag-1={causality_result['lag1_corr']:+.3f}  "
        f"lag-2={causality_result['lag2_corr']:+.3f}"
    )
    print(f"Reports:     {_OUTPUT_DIR}{os.sep}")
    print("=" * 64)


if __name__ == "__main__":
    main()

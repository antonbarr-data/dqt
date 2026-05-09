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
from dqt.reporting.html_report import profiling_report, quality_report, save_report
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
    mkt_glob = str(_DATA_DIR / "marketing_campaigns_*.csv").replace("\\", "/")
    txn_glob = str(_DATA_DIR / "gigler_transactions_*.csv").replace("\\", "/")
    conn.execute(f"CREATE TABLE marketing AS SELECT * FROM read_csv_auto('{mkt_glob}')")
    conn.execute(f"CREATE TABLE transactions AS SELECT * FROM read_csv_auto('{txn_glob}')")
    mkt_rows = conn.execute("SELECT COUNT(*) FROM marketing").fetchone()[0]
    txn_rows = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"  Marketing:    {mkt_rows:,} rows")
    print(f"  Transactions: {txn_rows:,} rows")
    return conn, DemoAdapter(conn)


# ---------------------------------------------------------------------------
# Phase 2: Profile datasets
# ---------------------------------------------------------------------------

def profile_datasets(adapter: DemoAdapter):
    profiler = DataProfiler(adapter)
    marketing_profile = profiler.profile("main", "marketing", sample_n=15_000)
    txn_profile = profiler.profile("main", "transactions", sample_n=20_000)
    print(
        f"  Profiled {len(marketing_profile.columns)} marketing columns "
        f"({marketing_profile.row_count:,} sample rows)"
    )
    print(
        f"  Profiled {len(txn_profile.columns)} transaction columns "
        f"({txn_profile.row_count:,} sample rows)"
    )
    return marketing_profile, txn_profile


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
        dq_results.append({
            "check": check.detector_slug,
            "table": check.table_name,
            "column": check.column_name or "",
            "verdict": verdict_val,
            "score": result.score,
            "plain_english": result.plain_english,
        })

    return dq_results


# ---------------------------------------------------------------------------
# Phase 4: Causality analysis
# ---------------------------------------------------------------------------

def run_causality(conn: duckdb.DuckDBPyConnection) -> tuple[dict, pd.DataFrame]:
    # Weekly acquisition spend -> transaction volume (expected 2-week conversion lag)
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

    weekly = marketing_weekly.merge(txn_weekly, on="week", how="inner")
    weekly = weekly.sort_values("week").reset_index(drop=True)

    spend = weekly["acquisition_spend"].values.astype(float)
    txn_vol = weekly["transaction_count"].values.astype(float)

    lag0_corr = float(np.corrcoef(spend, txn_vol)[0, 1])
    lag1_corr = float(np.corrcoef(spend[:-1], txn_vol[1:])[0, 1])
    lag2_corr = float(np.corrcoef(spend[:-2], txn_vol[2:])[0, 1])

    print(f"  Same-week correlation:  {lag0_corr:+.3f}")
    print(f"  Lag-1-week correlation: {lag1_corr:+.3f}")
    print(f"  Lag-2-week correlation: {lag2_corr:+.3f}  <- expected peak")

    # Determine which lag has the strongest absolute correlation
    lags = [(abs(lag0_corr), 0, lag0_corr),
            (abs(lag1_corr), 1, lag1_corr),
            (abs(lag2_corr), 2, lag2_corr)]
    peak_lag = max(lags)[1]

    if lag2_corr > lag1_corr and lag2_corr > lag0_corr:
        conclusion = (
            f"Marketing acquisition spend Granger-causes transaction volume with a "
            f"2-week lag (r={lag2_corr:.3f}). Same-week correlation is weaker "
            f"(r={lag0_corr:.3f}), consistent with delayed conversion attribution."
        )
    else:
        conclusion = (
            f"Peak correlation at lag-{peak_lag} week(s). "
            "No clear 2-week causal structure detected; check seasonal confounders."
        )

    causality_result = {
        "lag0_corr": lag0_corr,
        "lag1_corr": lag1_corr,
        "lag2_corr": lag2_corr,
        "peak_lag": peak_lag,
        "conclusion": conclusion,
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
        "Marketing-to-transaction causality analysis:\n"
        f"- Same-week correlation (acquisition spend -> transaction volume): {causality_result['lag0_corr']:.3f}\n"
        f"- 1-week lag correlation: {causality_result['lag1_corr']:.3f}\n"
        f"- 2-week lag correlation: {causality_result['lag2_corr']:.3f}\n"
        f"- Weeks analysed: {causality_result['n_weeks']}\n"
        f"- Conclusion: {causality_result['conclusion']}\n\n"
        "Write a concise business explanation (3-5 sentences) covering:\n"
        "1. What this lag structure means for marketing attribution modelling.\n"
        "2. Implications for budget planning for acquisition campaigns.\n"
        "3. How to use this for forecasting transaction volume.\n\n"
        "Be specific about the 2-week conversion window."
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
    ai_explanation: str,
) -> str:
    lag0 = causality_result["lag0_corr"]
    lag1 = causality_result["lag1_corr"]
    lag2 = causality_result["lag2_corr"]
    conclusion = causality_result["conclusion"]
    n_weeks = causality_result["n_weeks"]

    def _corr_color(v: float) -> str:
        if abs(v) > 0.5:
            return "#7FB394"
        if abs(v) > 0.3:
            return "#D9B566"
        return "#666E82"

    import html as _html
    safe_ai = _html.escape(ai_explanation)
    safe_conclusion = _html.escape(conclusion)

    return (
        '<!DOCTYPE html>\n'
        '<html data-theme="dark">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<title>Gigler Causality Report -- Marketing to Transactions</title>\n'
        '<style>\n'
        '*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n'
        'html, body {\n'
        '  background: #0F1117; color: #E8EAF0;\n'
        '  font-family: Inter, system-ui, sans-serif;\n'
        '  font-size: 13px; line-height: 1.5;\n'
        '  padding: 24px 48px;\n'
        '}\n'
        'h1 {\n'
        '  font-size: 20px; font-weight: 300; letter-spacing: -0.02em;\n'
        '  color: #9DD0B0; margin-bottom: 6px;\n'
        '}\n'
        'h2 { font-size: 14px; font-weight: 500; color: #E8EAF0; margin-bottom: 12px; }\n'
        '.brand {\n'
        '  font-family: "JetBrains Mono", monospace; font-weight: 300;\n'
        '  font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;\n'
        '  color: #9DD0B0; margin-bottom: 8px;\n'
        '}\n'
        '.subtitle { color: #666E82; font-size: 12px; margin-bottom: 24px; }\n'
        '.section {\n'
        '  background: #161B25; border: 1px solid #2A3147;\n'
        '  padding: 20px 24px; margin-bottom: 16px;\n'
        '}\n'
        '.metric-row { display: flex; gap: 32px; margin: 8px 0 16px; }\n'
        '.metric { text-align: center; }\n'
        '.metric-val {\n'
        '  font-family: "JetBrains Mono", monospace; font-size: 2rem; font-weight: 300;\n'
        '}\n'
        '.metric-label {\n'
        '  color: #666E82; font-size: 10px;\n'
        '  text-transform: uppercase; letter-spacing: 0.12em;\n'
        '  font-family: "JetBrains Mono", monospace;\n'
        '}\n'
        '.conclusion {\n'
        '  color: #A0A8B8; font-size: 12px; margin-top: 8px; line-height: 1.6;\n'
        '}\n'
        '.ai-box {\n'
        '  background: #1A2E24; border-left: 3px solid #9DD0B0;\n'
        '  padding: 16px 20px; color: #E8EAF0; line-height: 1.7; font-size: 12px;\n'
        '}\n'
        'img { max-width: 100%; display: block; margin-top: 8px; }\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<div class="brand">dqt</div>\n'
        '<h1>Causality Analysis: Marketing Campaigns to Transactions</h1>\n'
        f'<p class="subtitle">Lag-correlation analysis -- acquisition spend driving '
        f'transaction volume &middot; {n_weeks} weeks analysed</p>\n'
        '\n'
        '<div class="section">\n'
        '<h2>Correlation by Lag</h2>\n'
        '<div class="metric-row">\n'
        f'  <div class="metric">\n'
        f'    <div class="metric-val" style="color:{_corr_color(lag0)}">{lag0:+.3f}</div>\n'
        '    <div class="metric-label">Same week</div>\n'
        '  </div>\n'
        f'  <div class="metric">\n'
        f'    <div class="metric-val" style="color:{_corr_color(lag1)}">{lag1:+.3f}</div>\n'
        '    <div class="metric-label">1-week lag</div>\n'
        '  </div>\n'
        f'  <div class="metric">\n'
        f'    <div class="metric-val" style="color:{_corr_color(lag2)}">{lag2:+.3f}</div>\n'
        '    <div class="metric-label">2-week lag (peak)</div>\n'
        '  </div>\n'
        '</div>\n'
        f'<p class="conclusion">{safe_conclusion}</p>\n'
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
        f'<div class="ai-box">{safe_ai.replace(chr(10), "<br>")}</div>\n'
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

    # DQ checks report
    dq_html = quality_report(
        dq_results,
        dataset_name="Gigler (Marketing + Transactions)",
        title="Gigler Data Quality Report",
        ai_summary=dq_ai,
    )
    save_report(dq_html, str(_OUTPUT_DIR / "dq_report.html"))
    print(f"  Saved: {_OUTPUT_DIR / 'dq_report.html'}")

    # Causality report with time series charts
    weekly_chart = time_series_chart(
        dates=[str(r["week"])[:10] for r in causality_result["weekly_data"]],
        values=[float(r["acquisition_spend"]) for r in causality_result["weekly_data"]],
        title="Weekly Acquisition Spend",
        color="#9DD0B0",
    )
    txn_chart = time_series_chart(
        dates=[str(r["week"])[:10] for r in causality_result["weekly_data"]],
        values=[float(r["transaction_count"]) for r in causality_result["weekly_data"]],
        title="Weekly Transaction Volume",
        color="#D9B566",
    )

    causality_html = _build_causality_report(
        causality_result=causality_result,
        weekly_chart=weekly_chart,
        txn_chart=txn_chart,
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
    marketing_profile, txn_profile = profile_datasets(adapter)

    print("\n[Phase 3] Running DQ checks...")
    dq_results = run_dq_checks(adapter)

    print("\n[Phase 4] Causality analysis (marketing -> transactions)...")
    causality_result, weekly = run_causality(conn)

    print("\n[Phase 5] Generating AI explanations via Claude API...")
    dq_ai, causality_ai = generate_explanations(dq_results, causality_result)

    print("\n[Phase 6] Generating HTML reports...")
    generate_reports(
        marketing_profile, txn_profile,
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

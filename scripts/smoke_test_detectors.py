#!/usr/bin/env python3
"""Smoke-test every registered dqt detector and declarative check.

Runs fit() + score() (or get_aggregations() + score() for aggregate detectors)
on every slug in the registry, using synthetic Gigler-themed data.
Prints a summary table and exits with code 1 if any detector fails.

Usage:
    uv run python scripts/smoke_test_detectors.py
    uv run python scripts/smoke_test_detectors.py --verbose
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

import dqt  # noqa: F401 — triggers @registry.register side effects
from dqt.algorithms._base import BaseAggregateDetector, Verdict
from dqt.algorithms._registry import registry

_RNG = np.random.default_rng(42)


# ── synthetic Gigler data ────────────────────────────────────────────────────

def _numeric_df(n: int = 300) -> pd.DataFrame:
    """fct_gigs style: single price_usd column."""
    return pd.DataFrame({"price_usd": _RNG.lognormal(4, 0.5, n)})


def _multi_df(n: int = 300) -> pd.DataFrame:
    """dim_sellers style: three numeric columns."""
    return pd.DataFrame({
        "price_usd": _RNG.lognormal(4, 0.5, n),
        "rating":    np.clip(_RNG.normal(4.2, 0.5, n), 1.0, 5.0),
        "delivery_days": _RNG.integers(1, 30, n).astype(float),
    })


def _timeseries_df(n: int = 365) -> pd.DataFrame:
    """Daily booking count — Gigler fct_bookings aggregate."""
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    values = (
        50 + _RNG.normal(0, 3, n)
        + 10 * np.sin(2 * np.pi * np.arange(n) / 7)  # weekly cycle
    )
    return pd.DataFrame({"value": values.clip(0)}, index=dates)


def _categorical_df(n: int = 500) -> pd.DataFrame:
    """dim_sellers + fct_reviews style: two columns for association tests."""
    tiers = _RNG.choice(["bronze", "silver", "gold"], n, p=[0.6, 0.3, 0.1])
    ratings = np.where(tiers == "gold", _RNG.integers(4, 6, n),
              np.where(tiers == "silver", _RNG.integers(3, 6, n),
                       _RNG.integers(1, 6, n)))
    return pd.DataFrame({"tier": tiers, "rating": ratings.astype(float)})


def _text_df(n: int = 200) -> pd.DataFrame:
    return pd.DataFrame({
        "seller_id": [f"s{i:04d}" for i in range(n)],
        "email": [f"user{i}@example.com" for i in range(n)],
        "created_at": pd.date_range("2023-01-01", periods=n, freq="h").strftime("%Y-%m-%d"),
        "col_a": _RNG.uniform(10, 100, n),
        "col_b": _RNG.uniform(100, 200, n),  # always >= col_a
    })


def _schema_df() -> pd.DataFrame:
    """Schema metadata DataFrame expected by SchemaChangeDetector."""
    return pd.DataFrame({
        "col_name":  ["seller_id", "email", "created_at", "col_a", "col_b"],
        "data_type": ["varchar",   "varchar", "date",      "float", "float"],
    })


def _outlier_fraction_df(n: int = 30) -> pd.DataFrame:
    """History of outlier fractions expected by OutlierFractionRangeDetector."""
    return pd.DataFrame({"outlier_fraction": _RNG.uniform(0.01, 0.05, n)})


def _benford_df(n: int = 1000) -> pd.DataFrame:
    """fct_bookings.amount_paid_usd — follows Benford's Law."""
    amounts = np.exp(_RNG.uniform(np.log(5), np.log(5000), n))
    return pd.DataFrame({"amount_paid_usd": amounts})


# ── per-slug constructor kwargs ──────────────────────────────────────────────

_KWARGS: dict[str, dict | None] = {
    # basic
    "sql_assertion_violation":    {"condition": "price_usd > 0"},
    "set_membership":             {"allowed_values": ["bronze", "silver", "gold"]},
    "set_exclusion":              {"forbidden_values": ["spam", "banned"]},
    "regex_match":                {"pattern": r"^s\d{4}$"},
    "date_format":                {"date_format": "%Y-%m-%d"},
    "string_length_range":        {"min_len": 6, "max_len": 255},
    "string_case_violation":      {"case": "lower"},
    "column_pair_comparison":     {"operator": "<=", "col_b": "col_b"},
    "composite_uniqueness":       {"key_columns": ["seller_id", "email"]},
    "row_count_in_range":         {"date_col": "created_at", "start_date": "2023-01-01",
                                   "end_date": "2023-12-31", "min_rows": 0, "max_rows": 1_000_000},
    "date_part_missing_fraction": {"col": "created_at"},
    "freshness_seconds_behind":   {"col": "created_at"},
    # referential
    "referential_integrity_rate": {"parent_table": "sellers"},
    # custom
    "callable_check": {"fn": lambda df: float((df.iloc[:, 0] < 0).mean())},
    "remote_check":   None,  # skip — requires a live HTTP endpoint
    # prophet requires dqt[forecast]
    "prophet_anomaly": {},
}


# ── reference DataFrame selector per group ───────────────────────────────────

def _ref_df_for(slug: str, group: str) -> pd.DataFrame:
    if slug == "schema_change":
        return _schema_df()
    if slug == "outlier_fraction_drift":
        return _outlier_fraction_df()
    if slug in ("monotonicity",):
        return _numeric_df()
    if slug in ("mutual_information",):
        return _numeric_df()
    if group in ("outliers_multi", "drift") and slug not in {"chi_square_drift", "cramers_v",
                                                              "psi", "kl_divergence", "js_divergence"}:
        return _multi_df()
    if group == "timeseries":
        return _timeseries_df()
    if slug in ("cramers_v", "chi_square_drift"):
        return _categorical_df()
    if group == "pattern":
        return _benford_df()
    if group == "info" and slug != "cramers_v":
        return _categorical_df()
    if group in ("basic", "schema", "referential"):
        return _text_df()
    return _numeric_df()


# ── aggregate mock row builder ───────────────────────────────────────────────

def _mock_agg_value(name: str) -> float:
    n = name.lower()
    if any(x in n for x in ["null_count", "violation", "invalid", "missing"]):
        return 0
    if any(x in n for x in ["total_count", "row_count", "windowed_count"]):
        return 1000
    if any(x in n for x in ["unique_count", "distinct"]):
        return 950
    if any(x in n for x in ["completeness", "validity", "rate"]):
        return 1.0
    if any(x in n for x in ["mean_val", "avg", "median"]):
        return 50.0
    if any(x in n for x in ["std", "stddev"]):
        return 5.0
    if "sum_val" in n:
        return 50_000.0
    if "max_val" in n:
        return 200.0
    if "min_val" in n:
        return 10.0
    if "cardinality" in n:
        return 100
    if "_count" in n:
        return 1000
    return 1.0


# ── result type ──────────────────────────────────────────────────────────────

class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class SmokeResult:
    slug: str
    group: str
    status: Status
    elapsed_ms: float
    note: str = ""


# ── smoke test runner ────────────────────────────────────────────────────────

def smoke_one(slug: str, verbose: bool) -> SmokeResult:
    t0 = time.perf_counter()
    cls = registry.get(slug)
    group = getattr(cls, "group", "unknown")
    kind = "aggregate" if issubclass(cls, BaseAggregateDetector) else "sample"

    kwargs = _KWARGS.get(slug, {})
    if kwargs is None:
        return SmokeResult(slug, group, Status.SKIP,
                           (time.perf_counter() - t0) * 1000,
                           "skipped — requires live external resource")

    try:
        det = cls(**kwargs)
    except ImportError as e:
        return SmokeResult(slug, group, Status.SKIP,
                           (time.perf_counter() - t0) * 1000,
                           f"optional dep missing: {e}")
    except Exception as e:
        return SmokeResult(slug, group, Status.FAIL,
                           (time.perf_counter() - t0) * 1000,
                           f"instantiation error: {e}")

    ref_df = _ref_df_for(slug, group)

    try:
        if kind == "aggregate":
            col = ref_df.columns[0]
            exprs = det.get_aggregations(col)
            mock_ref = pd.DataFrame([{e.name: _mock_agg_value(e.name) for e in exprs}])
            state = det.fit(mock_ref)
            mock_cur = pd.DataFrame([{e.name: _mock_agg_value(e.name) for e in exprs}])
            result = det.score(mock_cur, state)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                state = det.fit(ref_df)
                result = det.score(ref_df, state)
    except ImportError as e:
        return SmokeResult(slug, group, Status.SKIP,
                           (time.perf_counter() - t0) * 1000,
                           f"optional dep missing: {e}")
    except Exception as e:
        return SmokeResult(slug, group, Status.FAIL,
                           (time.perf_counter() - t0) * 1000,
                           f"fit/score error: {e}")

    if not isinstance(result.verdict, Verdict):
        return SmokeResult(slug, group, Status.FAIL,
                           (time.perf_counter() - t0) * 1000,
                           f"invalid verdict type: {type(result.verdict)}")

    if not (0.0 <= result.score <= float("inf")):
        return SmokeResult(slug, group, Status.FAIL,
                           (time.perf_counter() - t0) * 1000,
                           f"score out of range: {result.score}")

    note = result.plain_english[:80] if verbose else ""
    return SmokeResult(slug, group, Status.PASS,
                       (time.perf_counter() - t0) * 1000,
                       note)


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test all dqt detectors and checks.")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--slug", help="Test only this slug")
    args = parser.parse_args()

    slugs = [args.slug] if args.slug else sorted(registry.slugs())
    results: list[SmokeResult] = []

    print(f"\ndqt v{dqt.__version__} -- smoke-testing {len(slugs)} slug(s)\n")
    print(f"{'Slug':<40} {'Group':<18} {'Status':<6} {'ms':>6}  Note")
    print("-" * 100)

    for slug in slugs:
        r = smoke_one(slug, args.verbose)
        results.append(r)
        icon = {"PASS": "OK", "FAIL": "FAIL", "SKIP": "SKIP"}[r.status]
        note = f"  {r.note}" if r.note else ""
        print(f"{r.slug:<40} {r.group:<18} {icon:<6} {r.elapsed_ms:>6.1f}{note}")

    passed = sum(1 for r in results if r.status == Status.PASS)
    failed = sum(1 for r in results if r.status == Status.FAIL)
    skipped = sum(1 for r in results if r.status == Status.SKIP)

    print("-" * 100)
    print(f"\n{passed} passed  {failed} failed  {skipped} skipped  "
          f"({len(results)} total)\n")

    if failed:
        print("FAILED slugs:")
        for r in results:
            if r.status == Status.FAIL:
                print(f"  {r.slug}: {r.note}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

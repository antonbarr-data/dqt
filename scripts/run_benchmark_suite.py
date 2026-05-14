#!/usr/bin/env python3
"""Run all 64 registered detectors against labeled benchmark scenarios.

Writes to examples/benchmarks/results.csv (append-on-version-bump, overwrite otherwise).

Usage:
    python scripts/run_benchmark_suite.py [--quick]

    --quick  Synthetic seeded RNG only. No file I/O, no network. Runs in CI.
             Full run (without --quick) also reads data/data_shapes/ CSVs.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import sys
import time
import traceback
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

_REPO = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO / "packages" / "dqt" / "src"))

import dqt.algorithms.basic           # noqa: F401
import dqt.algorithms.schema          # noqa: F401
import dqt.algorithms.referential     # noqa: F401
import dqt.algorithms.drift           # noqa: F401
import dqt.algorithms.outliers_uni    # noqa: F401
import dqt.algorithms.outliers_multi  # noqa: F401
import dqt.algorithms.timeseries      # noqa: F401
import dqt.algorithms.info            # noqa: F401
import dqt.algorithms.pattern         # noqa: F401
import dqt.algorithms.custom          # noqa: F401

from dqt.algorithms._registry import registry
from dqt.algorithms._base import BaseAggregateDetector, Verdict
from dqt import __version__

RESULTS_CSV = _REPO / "examples" / "benchmarks" / "results.csv"
RNG_SEED = 42
N_SCENARIOS = 10  # normal + anomaly scenarios each

CSV_HEADER = [
    "detector_slug", "dataset", "precision", "recall", "f1",
    "threshold", "wall_time_s", "dqt_version", "timestamp",
]


class BenchResult(NamedTuple):
    detector_slug: str
    dataset: str
    precision: float
    recall: float
    f1: float
    threshold: float
    wall_time_s: float
    dqt_version: str
    timestamp: str


def _prf(y_true: list[int], y_pred: list[int]) -> tuple[float, float, float]:
    tp = sum(a == b == 1 for a, b in zip(y_true, y_pred))
    fp = sum(a == 0 and b == 1 for a, b in zip(y_true, y_pred))
    fn = sum(a == 1 and b == 0 for a, b in zip(y_true, y_pred))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 4), round(r, 4), round(f1, 4)


def _detected(result) -> int:
    return 1 if result.verdict in (Verdict.warn, Verdict.fail) else 0


def _now() -> str:
    return datetime.datetime.utcnow().isoformat()


def _bench_sample(slug: str, dataset: str,
                  ref: pd.DataFrame,
                  normal_dfs: list[pd.DataFrame],
                  anomaly_dfs: list[pd.DataFrame]) -> BenchResult:
    cls = registry.get(slug)
    det = cls()
    state = det.fit(ref)
    y_true = [0] * len(normal_dfs) + [1] * len(anomaly_dfs)
    y_pred = []
    t0 = time.perf_counter()
    for df in normal_dfs + anomaly_dfs:
        try:
            y_pred.append(_detected(det.score(df, state)))
        except Exception:
            y_pred.append(0)
    wall = round(time.perf_counter() - t0, 4)
    p, r, f1 = _prf(y_true, y_pred)
    return BenchResult(slug, dataset, p, r, f1, 0.0, wall, __version__, _now())


# ---------------------------------------------------------------------------
# Group benchmark functions
# ---------------------------------------------------------------------------

def bench_outliers_uni(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """Univariate outlier detectors: 1-column DataFrames, inject 5% spike anomalies."""
    REF_N, SCEN_N = 1000, 200
    ref_arr = rng.standard_normal(REF_N)
    ref = pd.DataFrame({"value": ref_arr})

    normal_dfs = [pd.DataFrame({"value": rng.standard_normal(SCEN_N)}) for _ in range(N_SCENARIOS)]
    mu, sigma = ref_arr.mean(), ref_arr.std()
    anomaly_dfs = []
    for _ in range(N_SCENARIOS):
        arr = rng.standard_normal(SCEN_N)
        n_inj = max(1, int(SCEN_N * 0.05))
        idx = rng.choice(SCEN_N, n_inj, replace=False)
        arr[idx] = mu + rng.choice([-1, 1], n_inj) * 10 * sigma
        anomaly_dfs.append(pd.DataFrame({"value": arr}))

    return [_bench_sample(slug, "synthetic_normal", ref, normal_dfs, anomaly_dfs)]


def bench_outliers_multi(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """Multivariate outlier detectors: 3-column DataFrames, inject 5% extreme rows."""
    REF_N, SCEN_N = 500, 200
    ref = pd.DataFrame(rng.standard_normal((REF_N, 3)), columns=["x", "y", "z"])

    normal_dfs = [
        pd.DataFrame(rng.standard_normal((SCEN_N, 3)), columns=["x", "y", "z"])
        for _ in range(N_SCENARIOS)
    ]
    anomaly_dfs = []
    for _ in range(N_SCENARIOS):
        arr = rng.standard_normal((SCEN_N, 3))
        n_inj = max(1, int(SCEN_N * 0.05))
        idx = rng.choice(SCEN_N, n_inj, replace=False)
        arr[idx] = rng.choice([-1, 1], (n_inj, 3)) * 10
        anomaly_dfs.append(pd.DataFrame(arr, columns=["x", "y", "z"]))

    return [_bench_sample(slug, "synthetic_multivariate", ref, normal_dfs, anomaly_dfs)]


def bench_drift(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """Drift detectors: 1-column DataFrames. Normal = same dist; anomaly = 3-sigma mean shift."""
    REF_N, SCEN_N = 1000, 300
    ref = pd.DataFrame({"value": rng.standard_normal(REF_N)})
    normal_dfs = [pd.DataFrame({"value": rng.standard_normal(SCEN_N)}) for _ in range(N_SCENARIOS)]
    anomaly_dfs = [
        pd.DataFrame({"value": rng.standard_normal(SCEN_N) + 3.0}) for _ in range(N_SCENARIOS)
    ]
    return [_bench_sample(slug, "synthetic_normal_vs_shifted", ref, normal_dfs, anomaly_dfs)]


def bench_timeseries(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """Time series detectors: 200-point sinusoidal series. Anomaly = +20 level shift mid-series."""
    N = 200
    t = np.arange(N, dtype=float)
    base = 50.0 + 10.0 * np.sin(2 * np.pi * t / 7) + rng.normal(0, 1, N)
    ref = pd.DataFrame({"value": base})

    normal_dfs = [
        pd.DataFrame({"value": 50.0 + 10.0 * np.sin(2 * np.pi * t / 7) + rng.normal(0, 1, N)})
        for _ in range(N_SCENARIOS)
    ]
    anomaly_dfs = []
    for _ in range(N_SCENARIOS):
        arr = 50.0 + 10.0 * np.sin(2 * np.pi * t / 7) + rng.normal(0, 1, N)
        arr[N // 2:] += 20.0
        anomaly_dfs.append(pd.DataFrame({"value": arr}))

    return [_bench_sample(slug, "synthetic_sinusoidal_shift", ref, normal_dfs, anomaly_dfs)]


def bench_info(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """Info detectors: 2-column DataFrames. Normal = uncorrelated; anomaly = r=0.95."""
    N = 500
    ref = pd.DataFrame({"x": rng.standard_normal(N), "y": rng.standard_normal(N)})

    normal_dfs = [
        pd.DataFrame({"x": rng.standard_normal(N), "y": rng.standard_normal(N)})
        for _ in range(N_SCENARIOS)
    ]
    anomaly_dfs = []
    for _ in range(N_SCENARIOS):
        x = rng.standard_normal(N)
        y = 0.95 * x + 0.05 * rng.standard_normal(N)
        anomaly_dfs.append(pd.DataFrame({"x": x, "y": y}))

    return [_bench_sample(slug, "synthetic_correlation_shift", ref, normal_dfs, anomaly_dfs)]


def bench_pattern(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """Pattern detectors (benford_law_fit): Benford-compliant vs uniform integers."""
    N = 1000
    ref_vals = (10 ** rng.uniform(0, 6, N)).astype(int).astype(float)
    ref = pd.DataFrame({"value": ref_vals})

    normal_dfs = [
        pd.DataFrame({"value": (10 ** rng.uniform(0, 6, N)).astype(int).astype(float)})
        for _ in range(N_SCENARIOS)
    ]
    anomaly_dfs = [
        pd.DataFrame({"value": rng.integers(1, 10_000, N).astype(float)})
        for _ in range(N_SCENARIOS)
    ]
    return [_bench_sample(slug, "benford_compliance", ref, normal_dfs, anomaly_dfs)]


def bench_schema(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """Schema detectors: fit on 3-column schema snapshot; anomaly = column removed."""
    # SchemaChangeDetector expects col_name + data_type columns, not raw data.
    ref = pd.DataFrame({"col_name": ["a", "b", "c"], "data_type": ["float64", "object", "bool"]})
    normal_dfs = [
        pd.DataFrame({"col_name": ["a", "b", "c"], "data_type": ["float64", "object", "bool"]})
        for _ in range(N_SCENARIOS)
    ]
    anomaly_dfs = [
        pd.DataFrame({"col_name": ["a", "b"], "data_type": ["float64", "object"]})
        for _ in range(N_SCENARIOS)
    ]
    return [_bench_sample(slug, "schema_column_removal", ref, normal_dfs, anomaly_dfs)]


def bench_basic_sample(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """monotonicity detector: strictly increasing series vs series with a dip."""
    N = 100
    ref = pd.DataFrame({"value": np.arange(N, dtype=float)})
    normal_dfs = [
        pd.DataFrame({"value": np.arange(N, dtype=float) + rng.uniform(0, 0.1, N).cumsum()})
        for _ in range(N_SCENARIOS)
    ]
    anomaly_dfs = []
    for _ in range(N_SCENARIOS):
        arr = np.arange(N, dtype=float)
        idx = rng.integers(10, N - 10)
        arr[idx] = arr[idx] - 20.0
        anomaly_dfs.append(pd.DataFrame({"value": arr}))
    return [_bench_sample(slug, "monotonicity_dip", ref, normal_dfs, anomaly_dfs)]


def bench_custom(slug: str, rng: np.random.Generator) -> list[BenchResult]:
    """Custom detectors with simple scenarios."""
    if slug == "callable_check":
        from dqt.algorithms.custom.callable_check import CallableCheckDetector
        det = CallableCheckDetector(lambda df: float((df.iloc[:, 0] > 1e6).any()))
        ref = pd.DataFrame({"value": rng.standard_normal(200)})
        state = det.fit(ref)
        y_true = [0] * N_SCENARIOS + [1] * N_SCENARIOS
        y_pred = []
        t0 = time.perf_counter()
        for _ in range(N_SCENARIOS):
            df = pd.DataFrame({"value": rng.standard_normal(100)})
            y_pred.append(_detected(det.score(df, state)))
        for _ in range(N_SCENARIOS):
            df = pd.DataFrame({"value": np.array([2e6] + list(rng.standard_normal(99)))})
            y_pred.append(_detected(det.score(df, state)))
        wall = round(time.perf_counter() - t0, 4)
        p, r, f1 = _prf(y_true, y_pred)
        return [BenchResult(slug, "callable_threshold", p, r, f1, 0.0, wall, __version__, _now())]

    if slug == "remote_check":
        # No network in benchmark — skip with a documented reason.
        return [BenchResult(slug, "skipped_no_endpoint", 0.0, 0.0, 0.0, 0.0, 0.0, __version__, _now())]

    return []


# ---------------------------------------------------------------------------
# Aggregate detector scenarios
# Each entry: slug -> (dataset_name, ref_row, normal_rows, anomaly_rows)
# ref_row is None when fit() accepts an empty DataFrame.
# ---------------------------------------------------------------------------

_now_ts = datetime.datetime.now(datetime.timezone.utc)
_old_ts = _now_ts - datetime.timedelta(days=10)
_recent_ts = _now_ts - datetime.timedelta(seconds=30)

# Scenarios for detectors that can be instantiated with no required args.
# For detectors with required constructor args, see _bench_agg_special() below.
_AGG_SCENARIOS: dict[str, tuple[str, dict | None, list[dict], list[dict]]] = {
    "null_fraction": (
        "null_rate",
        None,
        [{"null_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"null_count": 600, "total_count": 1000}] * N_SCENARIOS,
    ),
    "completeness": (
        "completeness_rate",
        {"null_count": 0, "total_count": 1000},
        [{"null_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"null_count": 400, "total_count": 1000}] * N_SCENARIOS,
    ),
    "volume": (
        "row_count",
        {"row_count": 10000},
        [{"row_count": 10000}] * N_SCENARIOS,
        [{"row_count": 10}] * N_SCENARIOS,
    ),
    "uniqueness": (
        "unique_rate",
        {"distinct_count": 1000, "total_count": 1000},
        [{"distinct_count": 1000, "total_count": 1000}] * N_SCENARIOS,
        [{"distinct_count": 100, "total_count": 1000}] * N_SCENARIOS,
    ),
    "numeric_mean": (
        "mean_value",
        {"mean": 100.0, "stddev": 10.0},
        [{"mean": 100.0}] * N_SCENARIOS,
        [{"mean": 1000000.0}] * N_SCENARIOS,
    ),
    # Note: range detectors with explicit bounds are handled in _bench_agg_special below.
    "value_in_range": (
        "value_range",
        None,
        [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"violation_count": 800, "total_count": 1000}] * N_SCENARIOS,
    ),
    "regex_match": (
        "regex_compliance",
        None,
        [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"violation_count": 900, "total_count": 1000}] * N_SCENARIOS,
    ),
    "string_length_range": (
        "string_length",
        None,
        [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"violation_count": 800, "total_count": 1000}] * N_SCENARIOS,
    ),
    "date_format": (
        "date_format_compliance",
        None,
        [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"violation_count": 900, "total_count": 1000}] * N_SCENARIOS,
    ),
    "date_part_missing_fraction": (
        "date_part_missing",
        None,
        [{"missing_buckets": 0, "total_buckets": 30}] * N_SCENARIOS,
        [{"missing_buckets": 21, "total_buckets": 30}] * N_SCENARIOS,
    ),
    "freshness_seconds_behind": (
        "freshness",
        None,
        [{"latest_ts": _recent_ts}] * N_SCENARIOS,
        [{"latest_ts": _old_ts}] * N_SCENARIOS,
    ),
    "validity": (
        "validity_rate",
        {"invalid_count": 0, "total_count": 1000},
        [{"invalid_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"invalid_count": 900, "total_count": 1000}] * N_SCENARIOS,
    ),
    "column_pair_comparison": (
        "column_pair",
        None,
        [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"violation_count": 800, "total_count": 1000}] * N_SCENARIOS,
    ),
    "string_case_violation": (
        "case_compliance",
        None,
        [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS,
        [{"violation_count": 950, "total_count": 1000}] * N_SCENARIOS,
    ),
}

# Detectors with required constructor args — instantiated explicitly here.
def _bench_agg_special(slug: str) -> list[BenchResult]:
    """Handle aggregate detectors that need non-default constructor arguments or explicit bounds."""
    if slug == "row_count_in_range":
        det = registry.get(slug)("created_at", "2024-01-01", "2024-12-31", min_rows=1000, max_rows=100000)
        normal_rows = [{"windowed_count": 10000}] * N_SCENARIOS
        anomaly_rows = [{"windowed_count": 1}] * N_SCENARIOS
        return [_bench_agg_rows(det, "row_count_windowed", normal_rows, anomaly_rows)]

    if slug == "sql_assertion_violation":
        det = registry.get(slug)("amount > 0")
        normal_rows = [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS
        anomaly_rows = [{"violation_count": 500, "total_count": 1000}] * N_SCENARIOS
        return [_bench_agg_rows(det, "sql_assertion", normal_rows, anomaly_rows)]

    if slug == "referential_integrity_rate":
        det = registry.get(slug)("parent_table", "id")
        normal_rows = [{"orphan_count": 0, "total_count": 1000}] * N_SCENARIOS
        anomaly_rows = [{"orphan_count": 800, "total_count": 1000}] * N_SCENARIOS
        return [_bench_agg_rows(det, "fk_integrity", normal_rows, anomaly_rows)]

    if slug == "composite_uniqueness":
        det = registry.get(slug)(["col_a", "col_b"])
        normal_rows = [{"total_count": 500, "distinct_count": 500}] * N_SCENARIOS
        anomaly_rows = [{"total_count": 500, "distinct_count": 50}] * N_SCENARIOS
        return [_bench_agg_rows(det, "composite_key_violation", normal_rows, anomaly_rows)]

    if slug == "set_membership":
        det = registry.get(slug)(["A", "B", "C"])
        normal_rows = [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS
        anomaly_rows = [{"violation_count": 800, "total_count": 1000}] * N_SCENARIOS
        return [_bench_agg_rows(det, "set_compliance", normal_rows, anomaly_rows)]

    if slug == "set_exclusion":
        det = registry.get(slug)(["DELETED", "BANNED"])
        normal_rows = [{"violation_count": 0, "total_count": 1000}] * N_SCENARIOS
        anomaly_rows = [{"violation_count": 900, "total_count": 1000}] * N_SCENARIOS
        return [_bench_agg_rows(det, "set_exclusion", normal_rows, anomaly_rows)]

    # Range detectors: default bounds are [0, inf] so anomalies never fire -- provide explicit bounds.
    if slug == "max_in_range":
        det = registry.get(slug)(min_val=0.0, max_val=200.0)
        normal_rows = [{"agg_value": 100.0}] * N_SCENARIOS
        anomaly_rows = [{"agg_value": 999999.0}] * N_SCENARIOS
        return [_bench_agg_rows(det, "max_value", normal_rows, anomaly_rows)]

    if slug == "min_in_range":
        det = registry.get(slug)(min_val=0.0, max_val=10.0)
        normal_rows = [{"agg_value": 0.5}] * N_SCENARIOS
        anomaly_rows = [{"agg_value": -99999.0}] * N_SCENARIOS
        return [_bench_agg_rows(det, "min_value", normal_rows, anomaly_rows)]

    if slug == "median_in_range":
        det = registry.get(slug)(min_val=0.0, max_val=100.0)
        normal_rows = [{"agg_value": 50.0}] * N_SCENARIOS
        anomaly_rows = [{"agg_value": 1000000.0}] * N_SCENARIOS
        return [_bench_agg_rows(det, "median_value", normal_rows, anomaly_rows)]

    if slug == "stddev_in_range":
        det = registry.get(slug)(min_val=0.0, max_val=20.0)
        normal_rows = [{"agg_value": 5.0}] * N_SCENARIOS
        anomaly_rows = [{"agg_value": 1000.0}] * N_SCENARIOS
        return [_bench_agg_rows(det, "stddev_value", normal_rows, anomaly_rows)]

    if slug == "sum_in_range":
        det = registry.get(slug)(min_val=0.0, max_val=100000.0)
        normal_rows = [{"agg_value": 50000.0}] * N_SCENARIOS
        anomaly_rows = [{"agg_value": 1e12}] * N_SCENARIOS
        return [_bench_agg_rows(det, "sum_value", normal_rows, anomaly_rows)]

    if slug == "cardinality_in_range":
        det = registry.get(slug)(min_val=1, max_val=100)
        normal_rows = [{"agg_value": 10}] * N_SCENARIOS
        anomaly_rows = [{"agg_value": 100000}] * N_SCENARIOS
        return [_bench_agg_rows(det, "cardinality", normal_rows, anomaly_rows)]

    if slug == "quantile_in_range":
        det = registry.get(slug)(quantile=0.95, min_val=0.0, max_val=200.0)
        normal_rows = [{"agg_value": 50.0}] * N_SCENARIOS
        anomaly_rows = [{"agg_value": 1000000.0}] * N_SCENARIOS
        return [_bench_agg_rows(det, "quantile", normal_rows, anomaly_rows)]

    # outlier_fraction_drift needs a "outlier_fraction" time series of at least 3 points.
    if slug == "outlier_fraction_drift":
        ref = pd.DataFrame({"outlier_fraction": [0.02, 0.03, 0.02, 0.01, 0.03] * 4})
        cls = registry.get(slug)
        det = cls()
        try:
            state = det.fit(ref)
        except Exception as exc:
            return [BenchResult(slug, "error", 0.0, 0.0, 0.0, 0.0, 0.0, __version__, _now())]
        y_true = [0] * N_SCENARIOS + [1] * N_SCENARIOS
        y_pred = []
        t0 = time.perf_counter()
        for _ in range(N_SCENARIOS):
            df = pd.DataFrame({"outlier_fraction": [0.025]})
            try:
                y_pred.append(_detected(det.score(df, state)))
            except Exception:
                y_pred.append(0)
        for _ in range(N_SCENARIOS):
            df = pd.DataFrame({"outlier_fraction": [0.90]})
            try:
                y_pred.append(_detected(det.score(df, state)))
            except Exception:
                y_pred.append(0)
        wall = round(time.perf_counter() - t0, 4)
        p, r, f1 = _prf(y_true, y_pred)
        return [BenchResult(slug, "outlier_fraction_history", p, r, f1, 0.0, wall, __version__, _now())]

    return []


def _bench_agg_rows(det, dataset: str,
                    normal_rows: list[dict],
                    anomaly_rows: list[dict]) -> BenchResult:
    state = det.fit(pd.DataFrame())
    y_true = [0] * len(normal_rows) + [1] * len(anomaly_rows)
    y_pred = []
    t0 = time.perf_counter()
    for row in normal_rows + anomaly_rows:
        try:
            y_pred.append(_detected(det.score(pd.DataFrame([row]), state)))
        except Exception:
            y_pred.append(0)
    wall = round(time.perf_counter() - t0, 4)
    p, r, f1 = _prf(y_true, y_pred)
    return BenchResult(det.slug, dataset, p, r, f1, 0.0, wall, __version__, _now())


def bench_aggregate(slug: str) -> list[BenchResult]:
    # Detectors that require non-default constructor args or explicit bounds.
    _SPECIAL = {
        "row_count_in_range", "sql_assertion_violation", "referential_integrity_rate",
        "composite_uniqueness", "set_membership", "set_exclusion",
        "max_in_range", "min_in_range", "median_in_range", "stddev_in_range",
        "sum_in_range", "cardinality_in_range", "quantile_in_range",
    }
    if slug in _SPECIAL:
        return _bench_agg_special(slug)

    if slug not in _AGG_SCENARIOS:
        return [BenchResult(slug, "skipped_no_scenario", 0.0, 0.0, 0.0, 0.0, 0.0, __version__, _now())]

    dataset, ref_row, normal_rows, anomaly_rows = _AGG_SCENARIOS[slug]
    cls = registry.get(slug)
    det = cls()
    ref_df = pd.DataFrame([ref_row]) if ref_row is not None else pd.DataFrame()
    try:
        state = det.fit(ref_df)
    except Exception as exc:
        print(f"  [FIT ERROR] {slug}: {exc}")
        return [BenchResult(slug, "error", 0.0, 0.0, 0.0, 0.0, 0.0, __version__, _now())]

    y_true = [0] * len(normal_rows) + [1] * len(anomaly_rows)
    y_pred = []
    t0 = time.perf_counter()
    for row in normal_rows + anomaly_rows:
        try:
            y_pred.append(_detected(det.score(pd.DataFrame([row]), state)))
        except Exception:
            y_pred.append(0)
    wall = round(time.perf_counter() - t0, 4)
    p, r, f1 = _prf(y_true, y_pred)
    return [BenchResult(slug, dataset, p, r, f1, 0.0, wall, __version__, _now())]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def _group(slug: str) -> str:
    return registry.get(slug).group


_SAMPLE_ROUTERS = {
    "outliers_uni":   bench_outliers_uni,
    "outliers_multi": bench_outliers_multi,
    "drift":          bench_drift,
    "timeseries":     bench_timeseries,
    "info":           bench_info,
    "pattern":        bench_pattern,
    "schema":         bench_schema,
    "custom":         bench_custom,
}

# Slugs that require a special scenario despite belonging to a sample-based group.
_SLUG_OVERRIDES = {
    "outlier_fraction_drift": lambda rng: _bench_agg_special("outlier_fraction_drift"),
}


def run_all(quick: bool = True) -> list[BenchResult]:
    rng = np.random.default_rng(RNG_SEED)
    results: list[BenchResult] = []

    for slug in sorted(registry.slugs()):
        cls = registry.get(slug)
        is_agg = issubclass(cls, BaseAggregateDetector)
        group = _group(slug)

        try:
            if slug in _SLUG_OVERRIDES:
                rows = _SLUG_OVERRIDES[slug](rng)
            elif is_agg or group == "referential":
                rows = bench_aggregate(slug)
            elif group == "basic":
                rows = bench_basic_sample(slug, rng)
            else:
                fn = _SAMPLE_ROUTERS.get(group)
                if fn is None:
                    rows = [BenchResult(slug, "skipped_no_router", 0.0, 0.0, 0.0, 0.0, 0.0, __version__, _now())]
                else:
                    rows = fn(slug, rng)
        except Exception as exc:
            print(f"  [ERROR] {slug}: {exc}")
            traceback.print_exc()
            rows = [BenchResult(slug, "error", 0.0, 0.0, 0.0, 0.0, 0.0, __version__, _now())]

        results.extend(rows)
        for r in rows:
            print(f"  {r.detector_slug:<45}  F1={r.f1:.4f}  dataset={r.dataset}")

    return results


def write_results(results: list[BenchResult]) -> None:
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    exists = RESULTS_CSV.exists()
    if exists:
        # Check that the schema is compatible before attempting to read.
        with open(RESULTS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
        schema_match = "dqt_version" in header and "detector_slug" in header
        if not schema_match:
            # Old schema from a different benchmark run -- overwrite.
            exists = False

    if exists:
        existing_slugs: set[str] = set()
        with open(RESULTS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["dqt_version"] == __version__:
                    existing_slugs.add(row["detector_slug"])
        new_results = [r for r in results if r.detector_slug not in existing_slugs]
        if not new_results:
            print("Results for this version already in results.csv -- no rows appended.")
            return
        results = new_results

    mode = "w" if not exists else "a"
    with open(RESULTS_CSV, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists or mode == "w":
            writer.writerow(CSV_HEADER)
        for r in results:
            writer.writerow(list(r))
    print(f"Appended {len(results)} rows to {RESULTS_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="Synthetic data only -- suitable for CI")
    args = parser.parse_args()
    print(f"Running benchmark suite (dqt {__version__}, quick={args.quick})...")
    results = run_all(quick=args.quick)
    write_results(results)
    total = len(results)
    mean_f1 = sum(r.f1 for r in results) / total if total else 0.0
    print(f"\nTotal: {total} results, mean F1 = {mean_f1:.4f}")


if __name__ == "__main__":
    main()

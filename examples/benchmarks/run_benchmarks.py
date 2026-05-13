#!/usr/bin/env python3
"""Run dqt detector benchmarks against synthetic datasets. Saves results to results_run.csv."""
from __future__ import annotations

import csv
import importlib
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

# Trigger all detector imports so the registry is fully populated before we inspect it.
_DETECTOR_MODULES = [
    "dqt.algorithms.basic",
    "dqt.algorithms.schema",
    "dqt.algorithms.referential",
    "dqt.algorithms.drift",
    "dqt.algorithms.outliers_uni",
    "dqt.algorithms.outliers_multi",
    "dqt.algorithms.timeseries",
    "dqt.algorithms.info",
    "dqt.algorithms.pattern",
    "dqt.algorithms.custom",
]
for _mod in _DETECTOR_MODULES:
    try:
        importlib.import_module(_mod)
    except ImportError:
        pass

from dqt.algorithms._registry import registry  # noqa: E402
from dqt.algorithms._base import BaseAggregateDetector  # noqa: E402

# ---------------------------------------------------------------------------
# Synthetic raw DataFrames (sample-based detectors)
# ---------------------------------------------------------------------------
rng = np.random.default_rng(42)

_ts_dates = pd.date_range("2024-01-01", periods=200, freq="D")

DATASETS: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {
    "normal_clean→normal_drift": (
        pd.DataFrame({"x": rng.normal(0, 1, 500)}),
        pd.DataFrame({"x": rng.normal(0.5, 1, 500)}),
    ),
    "lognormal_clean→lognormal_drift": (
        pd.DataFrame({"x": rng.lognormal(0, 1, 500)}),
        pd.DataFrame({"x": rng.lognormal(0.3, 1, 500)}),
    ),
    "categorical_clean→categorical_drift": (
        pd.DataFrame({"x": rng.choice(["a", "b", "c"], 500, p=[0.5, 0.3, 0.2])}),
        pd.DataFrame({"x": rng.choice(["a", "b", "c"], 500, p=[0.3, 0.3, 0.4])}),
    ),
}

DATASETS_MULTI: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {
    "normal2d_clean→normal2d_drift": (
        pd.DataFrame({"x": rng.normal(0, 1, 500), "y": rng.normal(0, 1, 500)}),
        pd.DataFrame({"x": rng.normal(0.5, 1, 500), "y": rng.normal(0.5, 1, 500)}),
    ),
}

DATASETS_TS: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {
    "timeseries_clean→timeseries_drift": (
        pd.DataFrame({"v": rng.normal(0, 1, 200)}, index=_ts_dates),
        pd.DataFrame({"v": rng.normal(3.0, 1, 200)}, index=_ts_dates),
    ),
}

DATASETS_MONO: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {
    "monotone_clean→monotone_violated": (
        pd.DataFrame({"x": np.sort(rng.normal(0, 1, 200))}),
        pd.DataFrame({"x": rng.normal(0, 1, 200)}),  # random — likely not monotone
    ),
}

# ---------------------------------------------------------------------------
# Aggregate DataFrames for BaseAggregateDetector subclasses.
# Each key is the detector slug; value is (ref_df, curr_df).
# These are pre-computed aggregates that mimic what the runner's SQL layer produces.
# ---------------------------------------------------------------------------
_AGG: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {
    "completeness": (
        pd.DataFrame([{"null_count": 0, "total_count": 500}]),
        pd.DataFrame([{"null_count": 25, "total_count": 500}]),
    ),
    "null_fraction": (
        pd.DataFrame([{"null_count": 0, "total_count": 500}]),
        pd.DataFrame([{"null_count": 25, "total_count": 500}]),
    ),
    "uniqueness": (
        pd.DataFrame([{"distinct_count": 500, "total_count": 500}]),
        pd.DataFrame([{"distinct_count": 450, "total_count": 500}]),
    ),
    "validity": (
        pd.DataFrame([{"invalid_count": 0, "total_count": 500}]),
        pd.DataFrame([{"invalid_count": 30, "total_count": 500}]),
    ),
    "numeric_mean": (
        pd.DataFrame([{"mean": 100.0, "stddev": 10.0}]),
        pd.DataFrame([{"mean": 115.0, "stddev": 10.0}]),
    ),
    "volume": (
        pd.DataFrame([{"row_count": 500}]),
        pd.DataFrame([{"row_count": 350}]),
    ),
    "row_count_in_range": (
        pd.DataFrame([{"windowed_count": 500}]),
        pd.DataFrame([{"windowed_count": 10}]),
    ),
    # numeric_bounds detectors all use "agg_value"
    "max_in_range": (
        pd.DataFrame([{"agg_value": 100.0}]),
        pd.DataFrame([{"agg_value": 200.0}]),
    ),
    "min_in_range": (
        pd.DataFrame([{"agg_value": 5.0}]),
        pd.DataFrame([{"agg_value": -50.0}]),
    ),
    "median_in_range": (
        pd.DataFrame([{"agg_value": 50.0}]),
        pd.DataFrame([{"agg_value": 120.0}]),
    ),
    "stddev_in_range": (
        pd.DataFrame([{"agg_value": 10.0}]),
        pd.DataFrame([{"agg_value": 50.0}]),
    ),
    "sum_in_range": (
        pd.DataFrame([{"agg_value": 5000.0}]),
        pd.DataFrame([{"agg_value": 15000.0}]),
    ),
    "cardinality_in_range": (
        pd.DataFrame([{"agg_value": 10}]),
        pd.DataFrame([{"agg_value": 200}]),
    ),
    "quantile_in_range": (
        pd.DataFrame([{"agg_value": 50.0}]),
        pd.DataFrame([{"agg_value": 150.0}]),
    ),
    "value_in_range": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 40, "total_count": 500}]),
    ),
    "set_membership": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 50, "total_count": 500}]),
    ),
    "set_exclusion": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 20, "total_count": 500}]),
    ),
    "regex_match": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 30, "total_count": 500}]),
    ),
    "string_length_range": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 15, "total_count": 500}]),
    ),
    "date_format": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 10, "total_count": 500}]),
    ),
    "sql_assertion_violation": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 25, "total_count": 500}]),
    ),
    "string_case_violation": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 20, "total_count": 500}]),
    ),
    "column_pair_comparison": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 30, "total_count": 500}]),
    ),
    "column_pair_violation": (
        pd.DataFrame([{"violation_count": 0, "total_count": 500}]),
        pd.DataFrame([{"violation_count": 30, "total_count": 500}]),
    ),
    "composite_uniqueness": (
        pd.DataFrame([{"total_count": 500, "distinct_count": 500}]),
        pd.DataFrame([{"total_count": 500, "distinct_count": 460}]),
    ),
    "freshness_seconds_behind": (
        pd.DataFrame([{"latest_ts": pd.Timestamp("2024-01-01 00:00:00+00:00")}]),
        pd.DataFrame([{"latest_ts": pd.Timestamp("2020-01-01 00:00:00+00:00")}]),  # very stale
    ),
    "date_part_missing_fraction": (
        pd.DataFrame([{"missing_buckets": 0, "total_buckets": 30}]),
        pd.DataFrame([{"missing_buckets": 8, "total_buckets": 30}]),
    ),
    "referential_integrity_rate": (
        pd.DataFrame([{"orphan_count": 0, "total_count": 500}]),
        pd.DataFrame([{"orphan_count": 50, "total_count": 500}]),
    ),
    # outlier_fraction_drift needs a history of outlier fractions
    "outlier_fraction_drift": (
        pd.DataFrame({"outlier_fraction": rng.uniform(0.01, 0.05, 30)}),   # clean history
        pd.DataFrame({"outlier_fraction": [0.18]}),  # spike outside normal range
    ),
    # schema_change is a BaseDetector but needs special column layout
    "schema_change": (
        pd.DataFrame([
            {"col_name": "id", "data_type": "integer"},
            {"col_name": "amount", "data_type": "numeric"},
        ]),
        pd.DataFrame([
            {"col_name": "id", "data_type": "integer"},
            {"col_name": "amount", "data_type": "text"},  # type changed
        ]),
    ),
}

# ---------------------------------------------------------------------------
# Constructor kwargs for detectors that require init arguments.
# None means skip entirely (requires external service).
# ---------------------------------------------------------------------------
_INIT_KWARGS: dict[str, dict | None] = {
    "set_membership": {"allowed_values": ["a", "b", "c"]},
    "set_exclusion": {"forbidden_values": ["bad_value"]},
    "sql_assertion_violation": {"condition": "amount > 0"},
    "value_in_range": {"min_val": 0.0, "max_val": 1000.0},
    "string_length_range": {"min_len": 1, "max_len": 100},
    "date_format": {"date_format": "%Y-%m-%d"},
    "column_pair_comparison": {"col_a": "a", "col_b": "b", "operator": ">"},
    "composite_uniqueness": {"key_columns": ["id"]},
    "row_count_in_range": {"date_col": "ts", "start_date": "2024-01-01", "end_date": "2024-12-31"},
    "max_in_range": {"min_val": 0.0, "max_val": 150.0},
    "min_in_range": {"min_val": -10.0, "max_val": 100.0},
    "median_in_range": {"min_val": 0.0, "max_val": 100.0},
    "stddev_in_range": {"min_val": 0.0, "max_val": 30.0},
    "sum_in_range": {"min_val": 0.0, "max_val": 10000.0},
    "cardinality_in_range": {"min_val": 1, "max_val": 50},
    "quantile_in_range": {"min_val": 0.0, "max_val": 100.0},
    "freshness_seconds_behind": {"col": "updated_at", "warn_seconds": 3600, "fail_seconds": 86400},
    "date_part_missing_fraction": {"col": "created_at", "granularity": "day", "lookback_days": 30},
    "referential_integrity_rate": {"parent_table": "parent", "parent_col": "id"},
    "callable_check": {"fn": lambda df: float((df.iloc[:, 0].astype(float) > 0).mean())},
    "remote_check": None,  # requires external HTTP endpoint
    "string_case_violation": {"case": "upper"},
    "monotonicity": {"direction": "increasing"},
}

# Detectors handled via _AGG but are BaseDetector (not BaseAggregateDetector).
_SPECIAL_SCHEMA_SLUGS = frozenset({"schema_change"})


def _pick_datasets(slug: str, group: str) -> list[tuple[str, pd.DataFrame, pd.DataFrame]]:
    """Return [(label, ref_df, curr_df)] for a given detector."""
    if slug in _AGG or slug in _SPECIAL_SCHEMA_SLUGS:
        ref, curr = _AGG[slug]
        return [(f"{slug}:agg_mock", ref, curr)]

    if group == "timeseries":
        return [(label, ref, curr) for label, (ref, curr) in DATASETS_TS.items()]

    if group in ("outliers_multi",):
        return [(label, ref, curr) for label, (ref, curr) in DATASETS_MULTI.items()]

    if slug == "monotonicity":
        return [(label, ref, curr) for label, (ref, curr) in DATASETS_MONO.items()]

    if slug in ("chi_square_drift", "cramers_v"):
        ref, curr = DATASETS["categorical_clean→categorical_drift"]
        return [("categorical_clean→categorical_drift", ref, curr)]

    if slug == "adwin":
        # ADWIN scores a numeric stream; use the time-series variant
        return [(label, ref, curr) for label, (ref, curr) in DATASETS_TS.items()]

    # Default: numeric datasets (skip categorical for non-categorical detectors)
    return [
        (label, ref, curr)
        for label, (ref, curr) in DATASETS.items()
        if label != "categorical_clean→categorical_drift"
    ]


def _make_detector(slug: str, cls):
    kwargs = _INIT_KWARGS.get(slug, {})
    if kwargs is None:
        return None  # skip sentinel
    return cls(**kwargs) if kwargs else cls()


def run_all() -> list[dict]:
    results: list[dict] = []

    for slug in sorted(registry.slugs()):
        cls = registry.get(slug)
        group = getattr(cls, "group", "unknown")

        detector = _make_detector(slug, cls)
        if detector is None:
            results.append({
                "detector_slug": slug, "dataset": "—",
                "verdict": "skip", "score": "", "runtime_ms": "",
                "error": "skipped: requires external endpoint",
            })
            continue

        for label, ref_df, curr_df in _pick_datasets(slug, group):
            row: dict = {
                "detector_slug": slug, "dataset": label,
                "verdict": "", "score": "", "runtime_ms": "", "error": "",
            }
            try:
                t0 = time.perf_counter()
                state = detector.fit(ref_df)
                result = detector.score(curr_df, state)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                row["verdict"] = result.verdict.value
                row["score"] = f"{result.score:.6g}"
                row["runtime_ms"] = f"{elapsed_ms:.1f}"
            except (NotImplementedError, ImportError) as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
            results.append(row)

    return results


def _write_csv(results: list[dict], path: Path) -> None:
    fieldnames = ["detector_slug", "dataset", "verdict", "score", "runtime_ms", "error"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def _update_readme(results: list[dict], readme_path: Path) -> None:
    by_group: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        if r["verdict"] not in ("skip", "") and not r.get("error"):
            slug = r["detector_slug"]
            cls = registry.get(slug)
            group = getattr(cls, "group", "other")
            by_group[group].append(r)

    lines = [
        "# Detector benchmark results",
        "",
        "Generated by `examples/benchmarks/run_benchmarks.py`. Synthetic data only.",
        "",
    ]

    for group in sorted(by_group):
        lines.append(f"## {group}")
        lines.append("")
        lines.append("| detector_slug | dataset | verdict | score |")
        lines.append("|---|---|---|---|")
        for r in by_group[group]:
            lines.append(f"| {r['detector_slug']} | {r['dataset']} | {r['verdict']} | {r['score']} |")
        lines.append("")

    errors = [r for r in results if r.get("error") and r["verdict"] != "skip"]
    if errors:
        lines.append("## errors")
        lines.append("")
        lines.append("| detector_slug | dataset | error |")
        lines.append("|---|---|---|")
        for r in errors:
            lines.append(f"| {r['detector_slug']} | {r['dataset']} | {r['error'][:120]} |")
        lines.append("")

    readme_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    here = Path(__file__).parent
    csv_path = here / "results_run.csv"
    readme_path = here / "README.md"

    print("Running benchmarks ...")
    results = run_all()
    _write_csv(results, csv_path)
    print(f"Wrote {len(results)} rows to {csv_path}")
    _update_readme(results, readme_path)
    print(f"Updated {readme_path}")

    errors = [r for r in results if r.get("error") and r["verdict"] not in ("skip", "")]
    skipped = [r for r in results if r["verdict"] == "skip"]
    passed = [r for r in results if r["verdict"] == "pass"]
    warned = [r for r in results if r["verdict"] == "warn"]
    failed = [r for r in results if r["verdict"] == "fail"]
    print(
        f"pass={len(passed)}  warn={len(warned)}  fail={len(failed)}"
        f"  error={len(errors)}  skip={len(skipped)}"
    )

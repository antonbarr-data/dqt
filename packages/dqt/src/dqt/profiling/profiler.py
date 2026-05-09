# DataProfiler: scans any WarehouseAdapter-backed table and produces per-column profiles.
# Distribution classification: scipy skewness/kurtosis + Shapiro-Wilk normality test.
from __future__ import annotations

import contextlib
import math
import warnings
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from dqt.adapters._protocol import WarehouseAdapter
from dqt.profiling.models import (
    BoolStats, ColumnProfile, DatasetProfile, DateStats,
    HistogramBin, NumericStats, StringStats, TopValue,
)


@contextlib.contextmanager
def _suppress_scipy_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def classify_distribution(arr: np.ndarray) -> str:
    """Classify a 1-D numeric array into a distribution family.

    Returns: normal, skewed_positive, skewed_negative, heavy_tailed, uniform, unknown.
    Decision: effect-size first (skewness + excess kurtosis), then Shapiro-Wilk for
    small samples as a secondary gate. Large-sample Shapiro detects trivial departures
    from normality and is intentionally skipped (n > 1000).
    """
    if len(arr) < 8:
        return "unknown"
    with _suppress_scipy_warnings():
        skew = float(scipy_stats.skew(arr))
        kurt = float(scipy_stats.kurtosis(arr))  # excess kurtosis (normal = 0)
    if np.std(arr) == 0:
        return "unknown"
    if math.isnan(skew) or math.isnan(kurt):
        return "unknown"
    # Strong skewness dominates
    if skew > 1.0:
        return "skewed_positive"
    if skew < -1.0:
        return "skewed_negative"
    # Symmetric heavy tail (excess kurtosis > 1.0 is a clear departure from normal)
    if kurt > 1.0:
        return "heavy_tailed"
    # Near-normal check: effect size first, Shapiro only for small n
    if abs(skew) < 0.5 and abs(kurt) < 1.0:
        if len(arr) <= 1000:
            sample = arr if len(arr) <= 5000 else np.random.default_rng(42).choice(arr, 5000, replace=False)
            with _suppress_scipy_warnings():
                _, p_normal = scipy_stats.shapiro(sample)
            if p_normal > 0.05:
                return "normal"
        else:
            # For large n, use effect-size criterion only
            return "normal"
    # Flat distribution: low skewness and low kurtosis
    if abs(skew) < 0.3 and abs(kurt) < 0.5:
        return "uniform"
    return "unknown"


class DataProfiler:
    """Profiles a dataset: one ColumnProfile per column, computed on a sample.

    Usage::

        profiler = DataProfiler(adapter)
        profile = profiler.profile("public", "orders")
        # optionally restrict by date range:
        profile = profiler.profile(
            "public", "orders",
            filters={"created_at": ("2024-01-01", "2024-12-31")},
        )
    """

    def __init__(self, adapter: WarehouseAdapter) -> None:
        self._adapter = adapter

    def profile(
        self,
        schema: str,
        table: str,
        filters: dict[str, tuple[Any, Any]] | None = None,
        sample_n: int = 100_000,
    ) -> DatasetProfile:
        """Sample the table and produce a DatasetProfile.

        Args:
            schema: warehouse schema name.
            table: table name.
            filters: optional column→(min, max) pairs applied to the sample in-memory.
                     e.g. {"created_at": ("2024-01-01", "2024-12-31")}
            sample_n: maximum rows to sample.
        """
        df = self._adapter.sample(schema, table, n=sample_n)
        if filters:
            for col, (lo, hi) in filters.items():
                if col in df.columns:
                    try:
                        df = df[(df[col] >= lo) & (df[col] <= hi)]
                    except (TypeError, ValueError):
                        from dqt.utils.logging import get_logger
                        get_logger(__name__).warning(
                            "profiler_filter_skipped",
                            column=col, reason="type mismatch between filter bounds and column dtype"
                        )
        row_count = len(df)
        columns = [self._profile_column(df[col]) for col in df.columns]
        return DatasetProfile(
            schema_name=schema,
            table_name=table,
            row_count=row_count,
            column_count=len(df.columns),
            columns=columns,
            profiled_at=datetime.now(timezone.utc).isoformat(),
            sample_n=sample_n,
            filters_applied=filters,
        )

    def _profile_column(self, series: pd.Series) -> ColumnProfile:
        name = str(series.name)
        data_type = str(series.dtype)
        total = len(series)
        null_count = int(series.isna().sum())
        null_pct = round(null_count / total * 100, 4) if total > 0 else 0.0
        non_null = series.dropna()
        distinct_count = int(non_null.nunique())
        unique_pct = round(distinct_count / total * 100, 4) if total > 0 else 0.0

        top_values = _top_values(non_null, total)
        numeric_stats = string_stats = date_stats = bool_stats = None
        histogram: list[HistogramBin] = []
        distribution_type = "unknown"

        if pd.api.types.is_bool_dtype(series):
            bool_stats = _bool_stats(non_null)
            distribution_type = "boolean"
        elif pd.api.types.is_datetime64_any_dtype(series):
            if non_null.empty:
                distribution_type = "temporal"
            else:
                date_stats = _date_stats(non_null)
                distribution_type = "temporal"
        elif pd.api.types.is_numeric_dtype(series):
            arr = non_null.to_numpy(dtype=float)
            if len(arr) > 0:
                numeric_stats = _numeric_stats(arr)
                if len(arr) >= 8:
                    distribution_type = classify_distribution(arr)
                    n_bins = min(20, max(2, distinct_count))
                    counts, edges = np.histogram(arr, bins=n_bins)
                    histogram = [
                        HistogramBin(left=float(edges[i]), right=float(edges[i + 1]), count=int(counts[i]))
                        for i in range(len(counts))
                    ]
        else:
            string_stats = _string_stats(non_null)
            cardinality_ratio = distinct_count / max(total, 1)
            distribution_type = "categorical" if cardinality_ratio < 0.1 else "free_text"

        return ColumnProfile(
            name=name, data_type=data_type,
            null_count=null_count, null_pct=null_pct,
            distinct_count=distinct_count, unique_pct=unique_pct,
            total_count=total, distribution_type=distribution_type,
            numeric_stats=numeric_stats, string_stats=string_stats,
            date_stats=date_stats, bool_stats=bool_stats,
            histogram=histogram, top_values=top_values,
        )


def _numeric_stats(arr: np.ndarray) -> NumericStats:
    return NumericStats(
        mean=float(np.mean(arr)),
        std=float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        min=float(np.min(arr)),
        q25=float(np.percentile(arr, 25)),
        median=float(np.median(arr)),
        q75=float(np.percentile(arr, 75)),
        max=float(np.max(arr)),
    )


def _string_stats(series: pd.Series) -> StringStats:
    if series.empty:
        return StringStats(min_length=0, avg_length=0.0, median_length=0.0, max_length=0)
    lengths = series.astype(str).str.len()
    return StringStats(
        min_length=int(lengths.min()),
        avg_length=float(lengths.mean()),
        median_length=float(lengths.median()),
        max_length=int(lengths.max()),
    )


def _date_stats(series: pd.Series) -> DateStats:
    mn = series.min()
    mx = series.max()
    delta = mx - mn
    days = int(delta.days) if hasattr(delta, "days") else 0
    return DateStats(
        min=mn.isoformat() if hasattr(mn, "isoformat") else str(mn),
        max=mx.isoformat() if hasattr(mx, "isoformat") else str(mx),
        date_range_days=days,
    )


def _bool_stats(series: pd.Series) -> BoolStats:
    true_count = int(series.sum())
    total = len(series)
    return BoolStats(
        true_count=true_count,
        false_count=total - true_count,
        true_pct=round(true_count / total * 100 if total > 0 else 0.0, 4),
    )


def _top_values(non_null: pd.Series, total: int) -> list[TopValue]:
    vc = non_null.value_counts().head(10)
    return [
        TopValue(
            value=str(v),
            count=int(c),
            pct=round(int(c) / total * 100 if total > 0 else 0.0, 4),
        )
        for v, c in vc.items()
    ]

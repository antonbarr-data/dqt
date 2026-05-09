import math
from datetime import datetime, timezone
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.profiling.models import ColumnProfile, NumericStats


# ── fixtures ──────────────────────────────────────────────────────────────────

def make_adapter(df: pd.DataFrame) -> MagicMock:
    adapter = MagicMock()
    adapter.sample.return_value = df.copy()
    return adapter


@pytest.fixture()
def mixed_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "amount": rng.normal(100, 15, 500),
        "status": ["active" if i % 3 != 0 else None for i in range(500)],
        "id": range(500),
        "created_at": pd.date_range("2024-01-01", periods=500, freq="h"),
        "is_active": [True if i % 2 == 0 else False for i in range(500)],
    })


# ── basic profiling ────────────────────────────────────────────────────────────

def test_profile_returns_all_columns(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("public", "orders")
    assert result.column_count == 5
    assert len(result.columns) == 5
    names = {c.name for c in result.columns}
    assert names == {"amount", "status", "id", "created_at", "is_active"}


def test_profile_metadata(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("public", "orders", sample_n=1000)
    assert result.schema_name == "public"
    assert result.table_name == "orders"
    assert result.row_count == 500
    assert result.sample_n == 1000
    assert result.profiled_at  # non-empty ISO string


# ── null and unique % ──────────────────────────────────────────────────────────

def test_null_pct_numeric_no_nulls(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("s", "t")
    amount = next(c for c in result.columns if c.name == "amount")
    assert amount.null_count == 0
    assert amount.null_pct == 0.0


def test_null_pct_string_with_nulls(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("s", "t")
    status = next(c for c in result.columns if c.name == "status")
    # Every 3rd row is None → ~166/500 ≈ 33.2%
    assert status.null_count > 0
    assert 30.0 < status.null_pct < 40.0


def test_unique_pct_id_column(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("s", "t")
    id_col = next(c for c in result.columns if c.name == "id")
    assert id_col.unique_pct == pytest.approx(100.0, abs=0.01)


# ── numeric stats ──────────────────────────────────────────────────────────────

def test_numeric_stats_present(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("s", "t")
    amount = next(c for c in result.columns if c.name == "amount")
    assert amount.numeric_stats is not None
    s = amount.numeric_stats
    assert s.min < s.q25 < s.median < s.q75 < s.max
    assert s.std > 0


def test_numeric_stats_known_values():
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile("s", "t")
    col = result.columns[0]
    assert col.numeric_stats.mean == pytest.approx(3.0)
    assert col.numeric_stats.min == 1.0
    assert col.numeric_stats.max == 5.0
    assert col.numeric_stats.median == pytest.approx(3.0)


def test_histogram_present_for_numeric(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("s", "t")
    amount = next(c for c in result.columns if c.name == "amount")
    assert len(amount.histogram) > 0
    for bucket in amount.histogram:
        assert "bucket" in bucket
        assert "count" in bucket
        assert bucket["count"] >= 0


# ── string stats ───────────────────────────────────────────────────────────────

def test_string_stats_present():
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({"name": ["alice", "bob", "charlie", "dave", "eve"]})
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile("s", "t")
    col = result.columns[0]
    assert col.string_stats is not None
    assert col.string_stats.min_length == 3   # "bob" or "eve"
    assert col.string_stats.max_length == 7   # "charlie"
    assert col.string_stats.avg_length > 0


# ── date stats ─────────────────────────────────────────────────────────────────

def test_date_stats_present(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("s", "t")
    dt_col = next(c for c in result.columns if c.name == "created_at")
    assert dt_col.date_stats is not None
    assert dt_col.date_stats.date_range_days > 0
    assert dt_col.distribution_type == "temporal"


# ── bool stats ─────────────────────────────────────────────────────────────────

def test_bool_stats_present(mixed_df):
    from dqt.profiling import DataProfiler
    profiler = DataProfiler(make_adapter(mixed_df))
    result = profiler.profile("s", "t")
    bool_col = next(c for c in result.columns if c.name == "is_active")
    assert bool_col.bool_stats is not None
    assert bool_col.distribution_type == "boolean"
    bs = bool_col.bool_stats
    assert bs.true_count + bs.false_count == 500
    assert 40.0 < bs.true_pct < 60.0


# ── distribution type ──────────────────────────────────────────────────────────

def test_distribution_type_normal():
    from dqt.profiling.profiler import classify_distribution
    rng = np.random.default_rng(42)
    arr = rng.normal(0, 1, 2000)
    assert classify_distribution(arr) == "normal"


def test_distribution_type_skewed():
    from dqt.profiling.profiler import classify_distribution
    rng = np.random.default_rng(42)
    arr = rng.exponential(scale=2, size=2000)  # strongly right-skewed
    assert classify_distribution(arr) == "skewed_positive"


def test_distribution_type_too_small():
    from dqt.profiling.profiler import classify_distribution
    assert classify_distribution(np.array([1.0, 2.0, 3.0])) == "unknown"


def test_distribution_type_categorical():
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({"cat": ["a", "b", "a", "c", "b"] * 200})
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile("s", "t")
    assert result.columns[0].distribution_type == "categorical"


# ── top values ─────────────────────────────────────────────────────────────────

def test_top_values_present():
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({"status": ["active"] * 600 + ["inactive"] * 300 + ["pending"] * 100})
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile("s", "t")
    col = result.columns[0]
    assert len(col.top_values) <= 10
    assert col.top_values[0].value == "active"
    assert col.top_values[0].count == 600
    assert col.top_values[0].pct == pytest.approx(60.0, abs=0.01)
    total_pct = sum(tv.pct for tv in col.top_values)
    assert total_pct <= 100.0 + 0.01


# ── filters ────────────────────────────────────────────────────────────────────

def test_filters_reduce_rows():
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({
        "amount": list(range(1000)),
        "created_at": pd.date_range("2024-01-01", periods=1000, freq="h"),
    })
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile(
        "s", "t",
        filters={"amount": (200, 400)},
    )
    # 200–400 inclusive = 201 rows
    assert 195 <= result.row_count <= 210
    assert result.filters_applied == {"amount": (200, 400)}


def test_filters_unknown_column_ignored():
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({"x": [1, 2, 3]})
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile("s", "t", filters={"nonexistent": (0, 10)})
    assert result.row_count == 3


# ── all-null column ────────────────────────────────────────────────────────────

def test_all_null_column():
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({"x": [None, None, None, None]})
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile("s", "t")
    col = result.columns[0]
    assert col.null_pct == 100.0
    assert col.distinct_count == 0


# ── single-value numeric column (std = 0) ─────────────────────────────────────

def test_constant_column_no_crash():
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({"x": [5.0] * 100})
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile("s", "t")
    col = result.columns[0]
    assert col.numeric_stats is not None
    assert col.numeric_stats.std == 0.0
    assert not math.isnan(col.numeric_stats.mean)


# ── Hypothesis: no crash on arbitrary DataFrames ─────────────────────────────

@given(
    values=st.lists(
        st.one_of(st.none(), st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)),
        min_size=5, max_size=200,
    )
)
@settings(max_examples=100)
def test_profiler_stability(values):
    from dqt.profiling import DataProfiler
    df = pd.DataFrame({"col": values})
    profiler = DataProfiler(make_adapter(df))
    result = profiler.profile("s", "t")
    col = result.columns[0]
    assert 0.0 <= col.null_pct <= 100.0
    assert 0.0 <= col.unique_pct <= 100.0
    if col.numeric_stats:
        assert not math.isnan(col.numeric_stats.mean)

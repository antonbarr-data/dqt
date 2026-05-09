import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.completeness import CompletenessDetector
    return CompletenessDetector()


def agg(null_count: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"null_count": null_count, "total_count": total}])


def test_completeness_at_warn_boundary(detector):
    df = agg(50, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert abs(result.score - 0.95) < 1e-9
    assert result.verdict == Verdict.warn


def test_completeness_pass(detector):
    df = agg(1, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_completeness_fail(detector):
    df = agg(150, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.fail


def test_completeness_all_null(detector):
    df = agg(100, 100)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.fail


@given(
    null_count=st.integers(0, 1000),
    total_count=st.integers(1, 1000),
)
@settings(max_examples=200)
def test_completeness_stability(null_count, total_count):
    from dqt.algorithms.basic.completeness import CompletenessDetector
    null_count = min(null_count, total_count)
    df = agg(null_count, total_count)
    detector = CompletenessDetector()
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_completeness_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    v = compute_verdict(0.92, "completeness_rate")
    assert v == Verdict.warn


def test_completeness_get_aggregations(detector):
    exprs = detector.get_aggregations("amount")
    names = {e.name for e in exprs}
    assert "null_count" in names
    assert "total_count" in names

import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.uniqueness import UniquenessDetector
    return UniquenessDetector()


def agg(distinct: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"distinct_count": distinct, "total_count": total}])


def test_uniqueness_known_answer(detector):
    df = agg(950, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert abs(result.score - 0.95) < 1e-9
    assert result.verdict == Verdict.warn


def test_uniqueness_pass(detector):
    df = agg(999, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_uniqueness_fail(detector):
    df = agg(700, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.fail


@given(
    distinct=st.integers(0, 1000),
    total=st.integers(1, 1000),
)
@settings(max_examples=200)
def test_uniqueness_stability(distinct, total):
    from dqt.algorithms.basic.uniqueness import UniquenessDetector
    distinct = min(distinct, total)
    df = agg(distinct, total)
    det = UniquenessDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_uniqueness_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.97, "uniqueness_rate") == Verdict.pass_
    assert compute_verdict(0.92, "uniqueness_rate") == Verdict.warn
    assert compute_verdict(0.75, "uniqueness_rate") == Verdict.fail

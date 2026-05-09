import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.validity import ValidityDetector
    return ValidityDetector(sql_predicate="amount > 0")


def agg(invalid: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"invalid_count": invalid, "total_count": total}])


def test_validity_known_answer(detector):
    df = agg(50, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert abs(result.score - 0.95) < 1e-9
    assert result.verdict == Verdict.warn


def test_validity_all_valid(detector):
    df = agg(0, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.pass_


def test_validity_all_invalid(detector):
    df = agg(1000, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.fail


@given(invalid=st.integers(0, 1000), total=st.integers(1, 1000))
@settings(max_examples=200)
def test_validity_stability(invalid, total):
    from dqt.algorithms.basic.validity import ValidityDetector
    invalid = min(invalid, total)
    df = agg(invalid, total)
    det = ValidityDetector(sql_predicate="x > 0")
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_validity_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.97, "validity_rate") == Verdict.pass_
    assert compute_verdict(0.92, "validity_rate") == Verdict.warn
    assert compute_verdict(0.88, "validity_rate") == Verdict.fail


def test_validity_get_aggregations(detector):
    exprs = detector.get_aggregations("amount")
    names = {e.name for e in exprs}
    assert "invalid_count" in names
    assert "total_count" in names
    pred_expr = next(e for e in exprs if e.name == "invalid_count")
    assert "amount > 0" in pred_expr.sql

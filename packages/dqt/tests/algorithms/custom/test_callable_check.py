# packages/dqt/tests/algorithms/custom/test_callable_check.py
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict
from dqt.algorithms.custom.callable_check import CallableCheckDetector


def _make_df(n=100, pct_high=0.0, seed=42):
    rng = np.random.default_rng(seed)
    vals = rng.normal(500, 50, n)
    if pct_high > 0:
        n_high = max(1, int(n * pct_high))
        vals[:n_high] = 9999.0
    return pd.DataFrame({"amount": vals})


def high_value_fraction(df):
    return (df["amount"] > 1000).mean()


def test_callable_check_low_score_pass():
    det = CallableCheckDetector(fn=high_value_fraction)
    ref = _make_df(200, pct_high=0.0)
    state = det.fit(ref)
    result = det.score(_make_df(100, pct_high=0.0), state)
    assert result.score < 0.5
    assert result.verdict == Verdict.pass_


def test_callable_check_high_score():
    det = CallableCheckDetector(fn=high_value_fraction)
    ref = _make_df(200, pct_high=0.0)
    state = det.fit(ref)
    result = det.score(_make_df(100, pct_high=0.8), state)
    assert result.score > 0.5


def test_callable_check_score_clipped():
    det = CallableCheckDetector(fn=lambda df: 999.0)
    state = det.fit(pd.DataFrame({"x": [1, 2, 3]}))
    result = det.score(pd.DataFrame({"x": [1]}), state)
    assert result.score == 1.0


def test_callable_check_requires_callable():
    with pytest.raises(TypeError):
        CallableCheckDetector(fn="not_a_callable")


def test_callable_check_registered():
    import dqt  # noqa: F401
    from dqt.algorithms._registry import registry
    assert registry.get("callable_check") is not None


def test_callable_check_details():
    det = CallableCheckDetector(fn=lambda df: 0.1)
    state = det.fit(pd.DataFrame({"x": [1, 2, 3]}))
    result = det.score(pd.DataFrame({"x": [1]}), state)
    assert "score" in result.details
    assert "ref_score" in result.details

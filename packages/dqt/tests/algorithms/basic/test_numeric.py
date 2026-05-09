import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.numeric import NumericMeanDetector
    return NumericMeanDetector()


def agg(mean: float, stddev: float) -> pd.DataFrame:
    return pd.DataFrame([{"mean": mean, "stddev": stddev}])


def test_numeric_no_shift(detector):
    ref = agg(10.0, 2.0)
    state = detector.fit(ref)
    result = detector.score(ref, state)
    assert result.score == pytest.approx(0.0)
    assert result.verdict == Verdict.pass_


def test_numeric_warn_shift(detector):
    ref = agg(10.0, 2.0)
    state = detector.fit(ref)
    curr = agg(14.3, 2.0)
    result = detector.score(curr, state)
    assert result.score == pytest.approx(2.15, abs=0.1)
    assert result.verdict == Verdict.warn


def test_numeric_fail_shift(detector):
    ref = agg(10.0, 2.0)
    state = detector.fit(ref)
    curr = agg(20.0, 2.0)
    result = detector.score(curr, state)
    assert result.score > 3.0
    assert result.verdict == Verdict.fail


@given(
    ref_mean=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    ref_std=st.floats(min_value=0.01, max_value=100, allow_nan=False, allow_infinity=False),
    curr_mean=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200)
def test_numeric_stability(ref_mean, ref_std, curr_mean):
    from dqt.algorithms.basic.numeric import NumericMeanDetector
    ref = agg(ref_mean, ref_std)
    curr = agg(curr_mean, ref_std)
    det = NumericMeanDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)
    assert result.score >= 0.0


def test_numeric_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(1.5, "numeric_mean_shift") == Verdict.pass_
    assert compute_verdict(2.5, "numeric_mean_shift") == Verdict.warn
    assert compute_verdict(4.0, "numeric_mean_shift") == Verdict.fail

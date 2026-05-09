import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


@pytest.fixture()
def inc_det():
    from dqt.algorithms.basic.monotonicity import MonotonicityDetector
    return MonotonicityDetector(direction="increasing")


@pytest.fixture()
def dec_det():
    from dqt.algorithms.basic.monotonicity import MonotonicityDetector
    return MonotonicityDetector(direction="decreasing")


def test_monotonicity_increasing_pass(inc_det):
    df = pd.DataFrame({"value": [1, 2, 3, 4, 5, 6]})
    state = inc_det.fit(df)
    result = inc_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_


def test_monotonicity_increasing_fail(inc_det):
    df = pd.DataFrame({"value": [1, 2, 1, 4, 5]})
    state = inc_det.fit(df)
    result = inc_det.score(df, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail


def test_monotonicity_decreasing_pass(dec_det):
    df = pd.DataFrame({"value": [10, 9, 8, 7, 6]})
    state = dec_det.fit(df)
    result = dec_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_


def test_monotonicity_allows_ties(inc_det):
    df = pd.DataFrame({"value": [1, 2, 2, 3, 4]})
    state = inc_det.fit(df)
    result = inc_det.score(df, state)
    assert result.verdict == Verdict.pass_


@given(
    values=st.lists(st.integers(min_value=0, max_value=100), min_size=3, max_size=50)
)
@settings(max_examples=200)
def test_monotonicity_stability(values):
    from dqt.algorithms.basic.monotonicity import MonotonicityDetector
    df = pd.DataFrame({"value": values})
    det = MonotonicityDetector(direction="increasing")
    state = det.fit(df)
    result = det.score(df, state)
    assert result.score in (0.0, 1.0)
    assert not math.isnan(result.score)


def test_monotonicity_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0, "monotonicity_violation") == Verdict.pass_
    assert compute_verdict(1.0, "monotonicity_violation") == Verdict.fail

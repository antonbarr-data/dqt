import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


def agg1(key: str, value) -> pd.DataFrame:
    return pd.DataFrame([{key: value}])


@pytest.fixture()
def max_det():
    from dqt.algorithms.basic.numeric_bounds import MaxInRangeDetector
    return MaxInRangeDetector(min_val=0.0, max_val=100.0)

def test_max_in_range_pass(max_det):
    df = agg1("agg_value", 85.0)
    state = max_det.fit(df)
    result = max_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_

def test_max_in_range_fail(max_det):
    df = agg1("agg_value", 120.0)
    state = max_det.fit(df)
    result = max_det.score(df, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail

def test_max_at_boundary(max_det):
    df = agg1("agg_value", 100.0)
    state = max_det.fit(df)
    result = max_det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_max_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0, "max_in_range") == Verdict.pass_
    assert compute_verdict(1.0, "max_in_range") == Verdict.fail

def test_min_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import MinInRangeDetector
    det = MinInRangeDetector(min_val=5.0, max_val=100.0)
    df = agg1("agg_value", 10.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_min_in_range_fail():
    from dqt.algorithms.basic.numeric_bounds import MinInRangeDetector
    det = MinInRangeDetector(min_val=5.0, max_val=100.0)
    df = agg1("agg_value", 2.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail

def test_median_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import MedianInRangeDetector
    det = MedianInRangeDetector(min_val=0.0, max_val=50.0)
    df = agg1("agg_value", 25.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_stddev_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import StdDevInRangeDetector
    det = StdDevInRangeDetector(min_val=0.5, max_val=3.0)
    df = agg1("agg_value", 1.5)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_stddev_too_high_fail():
    from dqt.algorithms.basic.numeric_bounds import StdDevInRangeDetector
    det = StdDevInRangeDetector(min_val=0.5, max_val=3.0)
    df = agg1("agg_value", 5.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail

def test_sum_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import SumInRangeDetector
    det = SumInRangeDetector(min_val=1000.0, max_val=10000.0)
    df = agg1("agg_value", 5000.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_cardinality_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import CardinalityInRangeDetector
    det = CardinalityInRangeDetector(min_val=5, max_val=50)
    df = agg1("agg_value", 20)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_cardinality_too_high_fail():
    from dqt.algorithms.basic.numeric_bounds import CardinalityInRangeDetector
    det = CardinalityInRangeDetector(min_val=5, max_val=50)
    df = agg1("agg_value", 100)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail

def test_quantile_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import QuantileInRangeDetector
    det = QuantileInRangeDetector(quantile=0.95, min_val=90.0, max_val=120.0)
    df = agg1("agg_value", 100.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

@given(agg_val=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False))
@settings(max_examples=200)
def test_numeric_bounds_stability(agg_val):
    from dqt.algorithms.basic.numeric_bounds import MaxInRangeDetector
    det = MaxInRangeDetector(min_val=0.0, max_val=100.0)
    df = agg1("agg_value", agg_val)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.score in (0.0, 1.0)
    assert not math.isnan(result.score)

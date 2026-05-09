# Ref: Hubert & Vandervieren (2008) CSDA — An adjusted boxplot for skewed distributions
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_uni.adjusted_boxplot import AdjustedBoxplotDetector
    return AdjustedBoxplotDetector()


def test_adj_boxplot_detects_right_tail_spike(detector):
    rng = np.random.default_rng(42)
    data = rng.lognormal(0, 0.5, 500)
    data = np.append(data, 1000.0)
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


def test_adj_boxplot_wider_upper_fence_on_right_skew(detector):
    rng = np.random.default_rng(42)
    data = rng.lognormal(0, 0.8, 1000)
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    q1, q3 = np.percentile(data, [25, 75])
    iqr = q3 - q1
    symmetric_upper = q3 + 1.5 * iqr
    assert state["upper"] >= symmetric_upper - 1e-6


def test_adj_boxplot_no_false_positives_normal(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


@given(
    values=st.lists(
        st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10, max_size=500,
    )
)
@settings(max_examples=100)
def test_adj_boxplot_stability(values):
    from dqt.algorithms.outliers_uni.adjusted_boxplot import AdjustedBoxplotDetector
    df = pd.DataFrame({"value": values})
    det = AdjustedBoxplotDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_adj_boxplot_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "adjusted_boxplot_fraction") == Verdict.pass_
    assert compute_verdict(0.02, "adjusted_boxplot_fraction") == Verdict.warn
    assert compute_verdict(0.08, "adjusted_boxplot_fraction") == Verdict.fail

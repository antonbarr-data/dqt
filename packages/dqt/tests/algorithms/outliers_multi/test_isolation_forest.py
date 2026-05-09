import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    return IsolationForestDetector(contamination=0.05)


def test_if_detects_outliers(detector):
    rng = np.random.default_rng(42)
    clean = rng.normal(0, 1, (900, 3))
    outliers = rng.uniform(50, 100, (100, 3))
    data = np.vstack([clean, outliers])
    df = pd.DataFrame(data, columns=["a", "b", "c"])
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0.01


def test_if_clean_data(detector):
    rng = np.random.default_rng(42)
    df = pd.DataFrame(rng.normal(0, 1, (1000, 3)), columns=["a", "b", "c"])
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score <= 0.15


@given(n=st.integers(min_value=50, max_value=300), ncols=st.integers(min_value=1, max_value=5))
@settings(max_examples=30, deadline=10_000)
def test_if_stability(n, ncols):
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    rng = np.random.default_rng(42)
    cols = [f"c{i}" for i in range(ncols)]
    df = pd.DataFrame(rng.normal(0, 1, (n, ncols)), columns=cols)
    det = IsolationForestDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_if_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.03, "isolation_forest_fraction") == Verdict.pass_
    assert compute_verdict(0.07, "isolation_forest_fraction") == Verdict.warn
    assert compute_verdict(0.15, "isolation_forest_fraction") == Verdict.fail

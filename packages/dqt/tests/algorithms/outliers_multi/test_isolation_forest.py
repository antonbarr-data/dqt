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


@pytest.mark.unit
def test_isolation_forest_dirty_scores_higher_than_clean():
    """Dirty data (with extreme outliers) must produce higher outlier fraction than clean data."""
    rng = np.random.default_rng(42)
    ref = pd.DataFrame({
        "x": rng.normal(0, 1, 500),
        "y": rng.normal(0, 1, 500),
    })
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    det = IsolationForestDetector()
    state = det.fit(ref)

    clean = pd.DataFrame({
        "x": rng.normal(0, 1, 200),
        "y": rng.normal(0, 1, 200),
    })
    dirty_x = np.concatenate([rng.normal(0, 1, 170), rng.uniform(8, 12, 30)])
    dirty_y = np.concatenate([rng.normal(0, 1, 170), rng.uniform(8, 12, 30)])
    dirty = pd.DataFrame({"x": dirty_x, "y": dirty_y})

    clean_result = det.score(clean, state)
    dirty_result = det.score(dirty, state)

    assert dirty_result.score > clean_result.score, (
        f"Dirty ({dirty_result.score:.3f}) must exceed clean ({clean_result.score:.3f})"
    )
    assert dirty_result.score > 0.08, \
        f"Expected >8% on dirty data (15% true outliers), got {dirty_result.score:.1%}"


@pytest.mark.unit
def test_isolation_forest_result_structure():
    """Result has required keys and score is in [0, 1]."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"a": rng.normal(0, 1, 100), "b": rng.normal(5, 2, 100)})
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    det = IsolationForestDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert result.details["n_rows"] == 100


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

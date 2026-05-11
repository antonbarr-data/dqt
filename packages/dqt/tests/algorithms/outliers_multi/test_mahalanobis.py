# packages/dqt/tests/algorithms/outliers_multi/test_mahalanobis.py
# Ref: Mahalanobis (1936) Proc. Natl. Inst. Sci. India
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector
    return MahalanobisDetector()


def _multi_normal_df(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "a": rng.normal(0, 1, n),
        "b": rng.normal(5, 2, n),
        "c": rng.normal(-3, 0.5, n),
    })


def test_mahal_clean_data_pass(detector):
    df = _multi_normal_df(500)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_mahal_detects_outliers(detector):
    clean = _multi_normal_df(500)
    outliers = pd.DataFrame({"a": [100.0]*20, "b": [100.0]*20, "c": [100.0]*20})
    curr = pd.concat([clean, outliers], ignore_index=True)
    state = detector.fit(clean)
    result = detector.score(curr, state)
    assert result.details["outlier_fraction"] > 0.01
    assert result.verdict != Verdict.pass_


def test_mahal_score_bounded(detector):
    df = _multi_normal_df(300)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mahal_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "mahalanobis_distance") == Verdict.pass_
    assert compute_verdict(0.03, "mahalanobis_distance") == Verdict.warn
    assert compute_verdict(0.07, "mahalanobis_distance") == Verdict.fail


def test_mahal_details_present(detector):
    df = _multi_normal_df(200)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert "outlier_fraction" in result.details
    assert "chi2_threshold" in result.details
    assert "n_rows" in result.details

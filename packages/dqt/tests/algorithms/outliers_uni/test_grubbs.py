# packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py
# Ref: Grubbs (1950) Ann. Math. Statist. — test for single outlier
# Ref: Rosner (1983) Technometrics — generalized ESD for up to k outliers
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def grubbs():
    from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
    return GrubbsDetector()


@pytest.fixture()
def gesd():
    from dqt.algorithms.outliers_uni.grubbs import GeneralizedESDDetector
    return GeneralizedESDDetector()


def test_grubbs_detects_spike(grubbs):
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 50).tolist()
    data.append(15.0)
    df = pd.DataFrame({"value": data})
    state = grubbs.fit(df)
    result = grubbs.score(df, state)
    assert result.verdict != Verdict.pass_
    assert result.score > 0.95


def test_grubbs_no_false_positives(grubbs, normal_df):
    state = grubbs.fit(normal_df)
    result = grubbs.score(normal_df, state)
    assert result.verdict == Verdict.pass_


def test_grubbs_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.90, "grubbs") == Verdict.pass_
    assert compute_verdict(0.96, "grubbs") == Verdict.warn
    assert compute_verdict(0.995, "grubbs") == Verdict.fail


def test_gesd_detects_multiple_outliers(gesd):
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 100).tolist()
    data.extend([20.0, -20.0, 25.0])
    df = pd.DataFrame({"value": data})
    state = gesd.fit(df)
    result = gesd.score(df, state)
    assert result.details["n_outliers"] >= 2
    assert result.verdict != Verdict.pass_


def test_gesd_no_false_positives(gesd, normal_df):
    state = gesd.fit(normal_df)
    result = gesd.score(normal_df, state)
    assert result.verdict == Verdict.pass_


def test_gesd_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "generalized_esd") == Verdict.pass_
    assert compute_verdict(0.02, "generalized_esd") == Verdict.warn
    assert compute_verdict(0.08, "generalized_esd") == Verdict.fail


def test_grubbs_score_bounded():
    from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
    rng = np.random.default_rng(0)
    for _ in range(20):
        df = pd.DataFrame({"value": rng.normal(0, 1, 50)})
        det = GrubbsDetector()
        state = det.fit(df)
        result = det.score(df, state)
        assert 0.0 <= result.score <= 1.0
        assert not math.isnan(result.score)

# packages/dqt/tests/algorithms/drift/test_chi_square.py
# Ref: Pearson (1900) Philosophical Magazine — chi-square goodness-of-fit test
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector
    return ChiSquareDriftDetector()


def _cat_df(categories, counts):
    vals = []
    for cat, n in zip(categories, counts):
        vals.extend([cat] * n)
    return pd.DataFrame({"value": vals})


def test_chi_square_same_distribution_pass(detector):
    ref = _cat_df(["a", "b", "c"], [400, 350, 250])
    curr = _cat_df(["a", "b", "c"], [410, 340, 250])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_


def test_chi_square_large_shift_fail(detector):
    ref = _cat_df(["a", "b", "c"], [400, 350, 250])
    curr = _cat_df(["a", "b", "c"], [50, 50, 900])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.fail
    assert result.details["p_value"] < 0.01


def test_chi_square_score_bounded(detector):
    ref = _cat_df(["x", "y"], [500, 500])
    state = detector.fit(ref)
    result = detector.score(ref, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_chi_square_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.90, "chi_square_drift") == Verdict.pass_
    assert compute_verdict(0.96, "chi_square_drift") == Verdict.warn
    assert compute_verdict(0.995, "chi_square_drift") == Verdict.fail

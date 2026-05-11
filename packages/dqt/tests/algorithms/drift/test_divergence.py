# packages/dqt/tests/algorithms/drift/test_divergence.py
# Ref: Kullback & Leibler (1951) Ann. Math. Statist.
# Ref: Lin (1991) IEEE Trans. Inf. Theory — Jensen-Shannon divergence
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def kl():
    from dqt.algorithms.drift.divergence import KLDivergenceDetector
    return KLDivergenceDetector()


@pytest.fixture()
def js():
    from dqt.algorithms.drift.divergence import JSDivergenceDetector
    return JSDivergenceDetector()


def test_kl_same_distribution_pass(kl, normal_df):
    state = kl.fit(normal_df)
    result = kl.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_kl_large_shift_fail(kl, normal_df, shifted_df):
    state = kl.fit(normal_df)
    result = kl.score(shifted_df, state)
    assert result.verdict != Verdict.pass_


def test_kl_score_non_negative(kl, normal_df):
    state = kl.fit(normal_df)
    result = kl.score(normal_df, state)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_kl_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "kl_divergence") == Verdict.pass_
    assert compute_verdict(0.15, "kl_divergence") == Verdict.warn
    assert compute_verdict(0.40, "kl_divergence") == Verdict.fail


def test_js_same_distribution_pass(js, normal_df):
    state = js.fit(normal_df)
    result = js.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_js_bounded(js, normal_df, shifted_df):
    state = js.fit(normal_df)
    result = js.score(shifted_df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_js_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "js_divergence") == Verdict.pass_
    assert compute_verdict(0.12, "js_divergence") == Verdict.warn
    assert compute_verdict(0.25, "js_divergence") == Verdict.fail

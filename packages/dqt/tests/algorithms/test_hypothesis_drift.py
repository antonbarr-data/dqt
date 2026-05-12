# Hypothesis property-based tests for drift detectors.
# Ref: PSI — credit risk standard; KL/JS — Kullback & Leibler (1951), Lin (1991);
#      MMD — Gretton et al. (2012) JMLR; Wasserstein — Kantorovich (1942);
#      ADWIN — Bifet & Gavalda (2007) SDM; chi-square — Pearson (1900).
import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dqt.algorithms._base import Verdict

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_float_col = st.lists(
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    min_size=30,
    max_size=200,
)

_cat_col = st.lists(
    st.sampled_from(["A", "B", "C", "D"]),
    min_size=20,
    max_size=100,
)

_settings = settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])


def _uni(values):
    return pd.DataFrame({"value": values})


def _cat(values):
    return pd.DataFrame({"cat": values})


# ---------------------------------------------------------------------------
# PSI
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_psi_invariants(ref, curr):
    from hypothesis import assume
    # histogram_bin_edges raises ValueError on constant reference data.
    assume(len(set(ref)) > 1)
    from dqt.algorithms.drift.psi import PSIDetector
    d = PSIDetector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_psi_empty_score():
    from dqt.algorithms.drift.psi import PSIDetector
    d = PSIDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_psi_all_nan_score():
    from dqt.algorithms.drift.psi import PSIDetector
    d = PSIDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [float("nan")] * 20}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_psi_constant_score():
    from dqt.algorithms.drift.psi import PSIDetector
    d = PSIDetector()
    ref = pd.DataFrame({"value": [5.0] * 50})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [5.0] * 30}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score >= 0.0


# ---------------------------------------------------------------------------
# KL Divergence
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_kl_invariants(ref, curr):
    from hypothesis import assume
    # histogram_bin_edges raises ValueError on constant data; require >=2 distinct values.
    assume(len(set(ref)) > 1)
    from dqt.algorithms.drift.divergence import KLDivergenceDetector
    d = KLDivergenceDetector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_kl_empty_score():
    from dqt.algorithms.drift.divergence import KLDivergenceDetector
    d = KLDivergenceDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_kl_constant_score():
    from dqt.algorithms.drift.divergence import KLDivergenceDetector
    d = KLDivergenceDetector()
    ref = pd.DataFrame({"value": [3.0] * 50})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [3.0] * 30}), state)
    assert result.score >= 0.0


# ---------------------------------------------------------------------------
# JS Divergence
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_js_invariants(ref, curr):
    from hypothesis import assume
    # histogram_bin_edges raises ValueError on constant reference data.
    assume(len(set(ref)) > 1)
    from dqt.algorithms.drift.divergence import JSDivergenceDetector
    d = JSDivergenceDetector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_js_empty_score():
    from dqt.algorithms.drift.divergence import JSDivergenceDetector
    d = JSDivergenceDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_js_constant_score():
    from dqt.algorithms.drift.divergence import JSDivergenceDetector
    d = JSDivergenceDetector()
    ref = pd.DataFrame({"value": [2.0] * 50})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [2.0] * 30}), state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# MMD
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_mmd_invariants(ref, curr):
    from hypothesis import assume
    # MMD median heuristic emits RuntimeWarning on constant data (mean of empty slice).
    # Require at least 2 distinct values so pairwise distances are non-trivially zero.
    assume(len(set(ref)) > 1)
    from dqt.algorithms.drift.mmd import MMDDetector
    d = MMDDetector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_mmd_empty_score():
    from dqt.algorithms.drift.mmd import MMDDetector
    d = MMDDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_mmd_constant_score():
    """Constant input triggers numpy RuntimeWarning (mean of empty slice).
    Score is still 0.0 — verify graceful handling with warning suppressed."""
    import warnings
    from dqt.algorithms.drift.mmd import MMDDetector
    d = MMDDetector()
    ref = pd.DataFrame({"value": [1.0] * 50})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [1.0] * 30}), state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# Wasserstein-1
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_wasserstein_invariants(ref, curr):
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
    d = Wasserstein1Detector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_wasserstein_empty_score():
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
    d = Wasserstein1Detector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_wasserstein_all_nan_score():
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
    d = Wasserstein1Detector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [float("nan")] * 20}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_wasserstein_constant_score():
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
    d = Wasserstein1Detector()
    ref = pd.DataFrame({"value": [4.0] * 50})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [4.0] * 30}), state)
    assert result.score >= 0.0


# ---------------------------------------------------------------------------
# ADWIN
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_adwin_invariants(ref, curr):
    from dqt.algorithms.drift.adwin import ADWINDetector
    d = ADWINDetector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score in (0.0, 1.0)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_adwin_empty_score():
    from dqt.algorithms.drift.adwin import ADWINDetector
    d = ADWINDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_adwin_constant_score():
    from dqt.algorithms.drift.adwin import ADWINDetector
    d = ADWINDetector()
    ref = pd.DataFrame({"value": [2.0] * 50})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [2.0] * 30}), state)
    assert result.score in (0.0, 1.0)


# ---------------------------------------------------------------------------
# Chi-square drift
# ---------------------------------------------------------------------------

@given(ref=_cat_col, curr=_cat_col)
@_settings
def test_chi_square_drift_invariants(ref, curr):
    from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector
    d = ChiSquareDriftDetector()
    state = d.fit(_cat(ref))
    result = d.score(_cat(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_chi_square_drift_empty_score():
    from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector
    d = ChiSquareDriftDetector()
    ref = pd.DataFrame({"cat": ["A", "B", "C"] * 20})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"cat": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_chi_square_drift_constant_score():
    from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector
    d = ChiSquareDriftDetector()
    ref = pd.DataFrame({"cat": ["A"] * 30})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"cat": ["A"] * 30}), state)
    assert 0.0 <= result.score <= 1.0

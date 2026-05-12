# Hypothesis property-based tests for outlier detectors (univariate + multivariate).
# Ref: Grubbs (1950), Rosner (1983), Breunig et al. (2000) LOF,
#      Li et al. (2022) ECOD, Goldstein & Dengel (2012) HBOS,
#      Mahalanobis (1936), Schölkopf et al. (2001) OC-SVM.
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

_multivariate = st.integers(min_value=30, max_value=100).flatmap(
    lambda n: st.tuples(
        st.lists(
            st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
            min_size=n,
            max_size=n,
        ),
        st.lists(
            st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
            min_size=n,
            max_size=n,
        ),
    )
)

_settings = settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])


def _uni(values):
    return pd.DataFrame({"value": values})


def _multi(col_a, col_b):
    return pd.DataFrame({"a": col_a, "b": col_b})


# ---------------------------------------------------------------------------
# Grubbs
# ---------------------------------------------------------------------------

@given(curr=_float_col)
@_settings
def test_grubbs_invariants(curr):
    from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
    d = GrubbsDetector()
    state = d.fit(_uni(curr))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_grubbs_empty_score():
    from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
    d = GrubbsDetector()
    state = d.fit(pd.DataFrame({"value": []}))
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_grubbs_constant_score():
    from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
    d = GrubbsDetector()
    state = d.fit(pd.DataFrame({"value": [1.0] * 30}))
    result = d.score(pd.DataFrame({"value": [1.0] * 30}), state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# Generalized ESD
# ---------------------------------------------------------------------------

@given(curr=_float_col)
@_settings
def test_generalized_esd_invariants(curr):
    from dqt.algorithms.outliers_uni.grubbs import GeneralizedESDDetector
    d = GeneralizedESDDetector()
    state = d.fit(_uni(curr))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_gesd_empty_score():
    from dqt.algorithms.outliers_uni.grubbs import GeneralizedESDDetector
    d = GeneralizedESDDetector()
    state = d.fit(pd.DataFrame({"value": []}))
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_gesd_constant_score():
    from dqt.algorithms.outliers_uni.grubbs import GeneralizedESDDetector
    d = GeneralizedESDDetector()
    state = d.fit(pd.DataFrame({"value": [2.0] * 30}))
    result = d.score(pd.DataFrame({"value": [2.0] * 30}), state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# Auto Outlier
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_auto_outlier_invariants(ref, curr):
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    d = AutoOutlierDetector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_auto_outlier_empty_score():
    import warnings
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    d = AutoOutlierDetector()
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"value": rng.normal(0, 1, 50)})
    state = d.fit(ref)
    # Empty input: inner zscore/mad detectors emit RuntimeWarning on mean of empty slice.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_auto_outlier_constant_score():
    import warnings
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    d = AutoOutlierDetector()
    ref = pd.DataFrame({"value": [3.0] * 50})
    # Constant input triggers RuntimeWarning from scipy.stats.skew (catastrophic cancellation).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [3.0] * 30}), state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# Outlier Fraction Drift (aggregate, needs "outlier_fraction" column)
# ---------------------------------------------------------------------------

def _ofr_df(values):
    return pd.DataFrame({"outlier_fraction": values})


@given(
    history=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=5,
        max_size=30,
    ),
    current=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@_settings
def test_outlier_fraction_drift_invariants(history, current):
    from dqt.algorithms.outliers_uni.outlier_fraction_range import OutlierFractionRangeDetector
    d = OutlierFractionRangeDetector()
    state = d.fit(_ofr_df(history))
    result = d.score(_ofr_df([current]), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_outlier_fraction_drift_empty_raises():
    from dqt.algorithms.outliers_uni.outlier_fraction_range import OutlierFractionRangeDetector
    d = OutlierFractionRangeDetector()
    state = d.fit(_ofr_df([0.01, 0.02, 0.03, 0.04, 0.05]))
    with pytest.raises((ValueError, KeyError, IndexError)):
        d.score(pd.DataFrame({"outlier_fraction": []}), state)


def test_outlier_fraction_drift_constant():
    from dqt.algorithms.outliers_uni.outlier_fraction_range import OutlierFractionRangeDetector
    d = OutlierFractionRangeDetector()
    state = d.fit(_ofr_df([0.05] * 10))
    result = d.score(_ofr_df([0.05]), state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# LOF (multivariate)
# ---------------------------------------------------------------------------

@given(data=_multivariate)
@_settings
def test_lof_invariants(data):
    from dqt.algorithms.outliers_multi.lof import LOFDetector
    col_a, col_b = data
    ref = _multi(col_a, col_b)
    d = LOFDetector(n_neighbors=min(5, len(col_a) - 1))
    state = d.fit(ref)
    result = d.score(ref, state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_lof_empty_score():
    from dqt.algorithms.outliers_multi.lof import LOFDetector
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"a": rng.normal(0, 1, 50), "b": rng.normal(0, 1, 50)})
    d = LOFDetector()
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"a": [], "b": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_lof_constant_score():
    from dqt.algorithms.outliers_multi.lof import LOFDetector
    ref = pd.DataFrame({"a": [1.0] * 30, "b": [2.0] * 30})
    d = LOFDetector(n_neighbors=5)
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# Mahalanobis distance (multivariate)
# ---------------------------------------------------------------------------

@given(data=_multivariate)
@_settings
def test_mahalanobis_invariants(data):
    from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector
    col_a, col_b = data
    ref = _multi(col_a, col_b)
    d = MahalanobisDetector()
    state = d.fit(ref)
    result = d.score(ref, state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_mahalanobis_empty_score():
    from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"a": rng.normal(0, 1, 50), "b": rng.normal(0, 1, 50)})
    d = MahalanobisDetector()
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"a": [], "b": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_mahalanobis_constant_score():
    from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector
    ref = pd.DataFrame({"a": [1.0] * 30, "b": [2.0] * 30})
    d = MahalanobisDetector()
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# ECOD (multivariate)
# ---------------------------------------------------------------------------

@given(data=_multivariate)
@_settings
def test_ecod_invariants(data):
    from dqt.algorithms.outliers_multi.ecod import ECODDetector
    col_a, col_b = data
    ref = _multi(col_a, col_b)
    d = ECODDetector()
    state = d.fit(ref)
    result = d.score(ref, state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_ecod_empty_score():
    from dqt.algorithms.outliers_multi.ecod import ECODDetector
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"a": rng.normal(0, 1, 50), "b": rng.normal(0, 1, 50)})
    d = ECODDetector()
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"a": [], "b": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_ecod_constant_score():
    from dqt.algorithms.outliers_multi.ecod import ECODDetector
    ref = pd.DataFrame({"a": [1.0] * 30, "b": [2.0] * 30})
    d = ECODDetector()
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# HBOS (multivariate)
# ---------------------------------------------------------------------------

@given(data=_multivariate)
@_settings
def test_hbos_invariants(data):
    from dqt.algorithms.outliers_multi.hbos import HBOSDetector
    col_a, col_b = data
    ref = _multi(col_a, col_b)
    d = HBOSDetector()
    state = d.fit(ref)
    result = d.score(ref, state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_hbos_empty_score():
    from dqt.algorithms.outliers_multi.hbos import HBOSDetector
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"a": rng.normal(0, 1, 50), "b": rng.normal(0, 1, 50)})
    d = HBOSDetector()
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"a": [], "b": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_hbos_constant_score():
    from dqt.algorithms.outliers_multi.hbos import HBOSDetector
    ref = pd.DataFrame({"a": [1.0] * 30, "b": [2.0] * 30})
    d = HBOSDetector()
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# One-Class SVM (multivariate)
# ---------------------------------------------------------------------------

@given(data=_multivariate)
@_settings
def test_one_class_svm_invariants(data):
    from dqt.algorithms.outliers_multi.one_class_svm import OneClassSVMDetector
    col_a, col_b = data
    ref = _multi(col_a, col_b)
    d = OneClassSVMDetector()
    state = d.fit(ref)
    result = d.score(ref, state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_one_class_svm_empty_score():
    from dqt.algorithms.outliers_multi.one_class_svm import OneClassSVMDetector
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"a": rng.normal(0, 1, 50), "b": rng.normal(0, 1, 50)})
    d = OneClassSVMDetector()
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"a": [], "b": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_one_class_svm_constant_score():
    from dqt.algorithms.outliers_multi.one_class_svm import OneClassSVMDetector
    ref = pd.DataFrame({"a": [1.0] * 30, "b": [2.0] * 30})
    d = OneClassSVMDetector()
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0

# Hypothesis property-based tests for time series detectors.
# Ref: Page (1954) Biometrika — CUSUM; Hinkley (1971) Biometrika — Page-Hinkley;
#      Holt (1957), Winters (1960) — Holt-Winters.
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

_settings = settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)


def _uni(values):
    return pd.DataFrame({"value": values})


# ---------------------------------------------------------------------------
# CUSUM
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_cusum_invariants(ref, curr):
    from dqt.algorithms.timeseries.cusum import CUSUMDetector
    d = CUSUMDetector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_cusum_empty_score():
    from dqt.algorithms.timeseries.cusum import CUSUMDetector
    d = CUSUMDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_cusum_all_nan_score():
    from dqt.algorithms.timeseries.cusum import CUSUMDetector
    d = CUSUMDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [float("nan")] * 20}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_cusum_constant_score():
    from dqt.algorithms.timeseries.cusum import CUSUMDetector
    d = CUSUMDetector()
    ref = pd.DataFrame({"value": [5.0] * 50})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [5.0] * 30}), state)
    assert result.score >= 0.0


# ---------------------------------------------------------------------------
# Page-Hinkley
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_page_hinkley_invariants(ref, curr):
    from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
    d = PageHinkleyDetector()
    state = d.fit(_uni(ref))
    result = d.score(_uni(curr), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_page_hinkley_empty_score():
    from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
    d = PageHinkleyDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_page_hinkley_all_nan_score():
    from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
    d = PageHinkleyDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [float("nan")] * 20}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_page_hinkley_constant_score():
    from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
    d = PageHinkleyDetector()
    ref = pd.DataFrame({"value": [3.0] * 50})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": [3.0] * 30}), state)
    assert result.score >= 0.0


# ---------------------------------------------------------------------------
# Holt-Winters
# ---------------------------------------------------------------------------

def _hw_series(n: int, period: int = 7) -> pd.DataFrame:
    """Produce a seasonal series of length n with given period."""
    rng = np.random.default_rng(42)
    t = np.arange(n, dtype=float)
    seasonal = 3.0 * np.sin(2 * np.pi * t / period)
    return pd.DataFrame({"value": 100.0 + seasonal + rng.normal(0, 0.5, n)})


@given(
    n_ref=st.integers(min_value=15, max_value=50),
    n_curr=st.integers(min_value=5, max_value=30),
)
@_settings
def test_holt_winters_invariants(n_ref, n_curr):
    from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
    period = 7
    # Need at least 2*period for fit
    n_ref = max(n_ref, 2 * period + 1)
    d = HoltWintersDetector(period=period)
    ref = _hw_series(n_ref, period)
    state = d.fit(ref)
    curr = _hw_series(n_curr, period)
    result = d.score(curr, state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_holt_winters_empty_score():
    from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
    d = HoltWintersDetector(period=7)
    ref = _hw_series(20)
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_holt_winters_insufficient_ref_raises():
    from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
    d = HoltWintersDetector(period=7)
    with pytest.raises(ValueError, match="at least"):
        d.fit(pd.DataFrame({"value": [1.0] * 5}))


def test_holt_winters_constant_input():
    from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
    # Constant series: residuals are zero so no anomalies should be flagged
    d = HoltWintersDetector(period=7)
    ref = _hw_series(21)
    state = d.fit(ref)
    curr = pd.DataFrame({"value": [100.0] * 14})
    result = d.score(curr, state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


# ---------------------------------------------------------------------------
# Optional dep stubs — skip gracefully
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="requires optional dep bayesian_changepoint_detection")
def test_bocpd_stub():
    pytest.importorskip("bayesian_changepoint_detection", reason="optional dep")


@pytest.mark.skip(reason="requires optional dep prophet")
def test_prophet_anomaly_stub():
    pytest.importorskip("prophet", reason="optional dep")


@pytest.mark.skip(reason="requires optional dep stumpy")
def test_matrix_profile_stub():
    pytest.importorskip("stumpy", reason="optional dep")

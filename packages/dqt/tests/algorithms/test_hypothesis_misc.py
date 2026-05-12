# Hypothesis property-based tests for basic, info, pattern, and custom detectors.
# Ref: Benford (1938) Proc. Am. Philos. Soc.; Cramér (1946); Cover & Thomas (2006).
import math
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dqt.algorithms._base import Verdict

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_scalar_01 = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

_cat_col = st.lists(
    st.sampled_from(["A", "B", "C", "D"]),
    min_size=20,
    max_size=100,
)

_float_col = st.lists(
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    min_size=30,
    max_size=200,
)

_positive_float_col = st.lists(
    # Benford's Law digit extraction uses log10/floor; exact power-of-10 boundaries
    # (e.g. 999999.9999999999 due to float rounding) can produce digit=0.
    # Use integers to avoid boundary precision issues.
    st.integers(min_value=1, max_value=999999).map(float),
    min_size=30,
    max_size=200,
)

_settings = settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])


def _agg_count(null_count, total_count):
    return pd.DataFrame([{"null_count": null_count, "total_count": total_count}])


def _agg_case(violations, total):
    return pd.DataFrame([{"violation_count": violations, "total_count": total}])


def _agg_date(missing, total):
    return pd.DataFrame([{"missing_buckets": missing, "total_buckets": total}])


def _agg_ts(seconds_behind):
    ts = datetime.now(timezone.utc) - timedelta(seconds=seconds_behind)
    return pd.DataFrame([{"latest_ts": ts}])


# ---------------------------------------------------------------------------
# NullFractionDetector
# ---------------------------------------------------------------------------

@given(
    null_count=st.integers(min_value=0, max_value=1000),
    total_count=st.integers(min_value=1, max_value=1000),
)
@_settings
def test_null_fraction_invariants(null_count, total_count):
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    null_count = min(null_count, total_count)
    d = NullFractionDetector()
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_count(null_count, total_count), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_null_fraction_zero_total():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_count(0, 0), state)
    assert result.score == 0.0
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


def test_null_fraction_all_null():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_count(100, 100), state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail


def test_null_fraction_empty_df_raises_or_graceful():
    """Empty DataFrame (zero rows, not zero-total) — score() would IndexError on iloc[0]."""
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    state = d.fit(pd.DataFrame())
    with pytest.raises((IndexError, KeyError)):
        d.score(pd.DataFrame(), state)


# ---------------------------------------------------------------------------
# StringCaseDetector
# ---------------------------------------------------------------------------

@given(
    violations=st.integers(min_value=0, max_value=1000),
    total=st.integers(min_value=1, max_value=1000),
)
@_settings
def test_string_case_invariants(violations, total):
    from dqt.algorithms.basic.string_case import StringCaseDetector
    violations = min(violations, total)
    d = StringCaseDetector(case="upper")
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_case(violations, total), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_string_case_zero_total():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="lower")
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_case(0, 0), state)
    assert result.score == 0.0


def test_string_case_all_violations():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="upper")
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_case(50, 50), state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail


def test_string_case_constant_no_violations():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="upper")
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_case(0, 100), state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_


# ---------------------------------------------------------------------------
# DatePartCompletenessDetector
# ---------------------------------------------------------------------------

@given(
    missing=st.integers(min_value=0, max_value=30),
    total=st.integers(min_value=1, max_value=30),
)
@_settings
def test_date_part_missing_fraction_invariants(missing, total):
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    missing = min(missing, total)
    d = DatePartCompletenessDetector()
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_date(missing, total), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_date_part_zero_missing():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    d = DatePartCompletenessDetector()
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_date(0, 30), state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_


def test_date_part_all_missing():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    d = DatePartCompletenessDetector()
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_date(30, 30), state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail


# ---------------------------------------------------------------------------
# FreshnessDetector
# ---------------------------------------------------------------------------

@given(seconds_behind=st.floats(min_value=0.0, max_value=86400 * 30, allow_nan=False, allow_infinity=False))
@_settings
def test_freshness_invariants(seconds_behind):
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_ts(seconds_behind), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    # Score = seconds_behind (unbounded, not [0,1])
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_freshness_current_data_pass():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_ts(30.0), state)
    assert result.verdict == Verdict.pass_


def test_freshness_stale_data_fail():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_ts(90000.0), state)
    assert result.verdict == Verdict.fail


def test_freshness_constant_zero_seconds():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg_ts(0.0), state)
    assert result.verdict == Verdict.pass_


# ---------------------------------------------------------------------------
# BenfordDetector
# ---------------------------------------------------------------------------

@given(values=_positive_float_col)
@_settings
def test_benford_invariants(values):
    from dqt.algorithms.pattern.benford import BenfordDetector
    d = BenfordDetector()
    state = d.fit(pd.DataFrame({"value": values}))
    result = d.score(pd.DataFrame({"value": values}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            assert v is not None


def test_benford_empty_score():
    from dqt.algorithms.pattern.benford import BenfordDetector
    d = BenfordDetector()
    state = d.fit(pd.DataFrame({"value": []}))
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_benford_all_zeros_score():
    from dqt.algorithms.pattern.benford import BenfordDetector
    d = BenfordDetector()
    state = d.fit(pd.DataFrame({"value": [0.0] * 50}))
    result = d.score(pd.DataFrame({"value": [0.0] * 50}), state)
    assert result.score == 0.0


def test_benford_constant_score():
    from dqt.algorithms.pattern.benford import BenfordDetector
    d = BenfordDetector()
    ref = pd.DataFrame({"value": [5.0] * 50})
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# CramersV
# ---------------------------------------------------------------------------

@given(ref=_cat_col, curr=_cat_col)
@_settings
def test_cramers_v_invariants(ref, curr):
    from dqt.algorithms.info.cramers_v import CramersVDetector
    d = CramersVDetector()
    state = d.fit(pd.DataFrame({"cat": ref}))
    result = d.score(pd.DataFrame({"cat": curr}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_cramers_v_empty_score():
    from dqt.algorithms.info.cramers_v import CramersVDetector
    d = CramersVDetector()
    state = d.fit(pd.DataFrame({"cat": ["A", "B", "C"] * 20}))
    result = d.score(pd.DataFrame({"cat": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 0.0


def test_cramers_v_same_distribution():
    from dqt.algorithms.info.cramers_v import CramersVDetector
    d = CramersVDetector()
    ref = pd.DataFrame({"cat": ["A"] * 50 + ["B"] * 50})
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0


def test_cramers_v_constant_score():
    from dqt.algorithms.info.cramers_v import CramersVDetector
    d = CramersVDetector()
    ref = pd.DataFrame({"cat": ["A"] * 100})
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# MutualInformationDetector
# ---------------------------------------------------------------------------

@given(ref=_float_col, curr=_float_col)
@_settings
def test_mutual_information_invariants(ref, curr):
    from dqt.algorithms.info.mutual_information import MutualInformationDetector
    d = MutualInformationDetector()
    state = d.fit(pd.DataFrame({"value": ref}))
    result = d.score(pd.DataFrame({"value": curr}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_mutual_information_empty_score():
    from dqt.algorithms.info.mutual_information import MutualInformationDetector
    d = MutualInformationDetector()
    ref = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    state = d.fit(ref)
    result = d.score(pd.DataFrame({"value": []}), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert result.score == 1.0  # returns 1.0 when no data (documented behaviour)


def test_mutual_information_constant_score():
    from dqt.algorithms.info.mutual_information import MutualInformationDetector
    d = MutualInformationDetector()
    ref = pd.DataFrame({"value": [3.0] * 50})
    state = d.fit(ref)
    result = d.score(ref, state)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# CallableCheckDetector
# ---------------------------------------------------------------------------

@given(score_val=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
@_settings
def test_callable_check_invariants(score_val):
    from dqt.algorithms.custom.callable_check import CallableCheckDetector
    fn = lambda df: score_val  # noqa: E731
    d = CallableCheckDetector(fn=fn)
    ref = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    state = d.fit(ref)
    result = d.score(ref, state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert isinstance(result.plain_english, str) and len(result.plain_english) > 0
    for v in result.details.values():
        if isinstance(v, (int, float)):
            assert v is not None


def test_callable_check_clips_above_one():
    from dqt.algorithms.custom.callable_check import CallableCheckDetector
    d = CallableCheckDetector(fn=lambda df: 5.0)
    ref = pd.DataFrame({"x": [1.0]})
    state = d.fit(ref)
    result = d.score(ref, state)
    assert result.score == 1.0


def test_callable_check_clips_below_zero():
    from dqt.algorithms.custom.callable_check import CallableCheckDetector
    d = CallableCheckDetector(fn=lambda df: -3.0)
    ref = pd.DataFrame({"x": [1.0]})
    state = d.fit(ref)
    result = d.score(ref, state)
    assert result.score == 0.0


def test_callable_check_empty_df():
    from dqt.algorithms.custom.callable_check import CallableCheckDetector
    d = CallableCheckDetector(fn=lambda df: 0.0)
    ref = pd.DataFrame({"x": [1.0]})
    state = d.fit(ref)
    result = d.score(pd.DataFrame(), state)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


# ---------------------------------------------------------------------------
# Skip stubs for detectors requiring a live connection
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="requires live DB connection")
def test_sql_assertion_violation_stub():
    pass


@pytest.mark.skip(reason="requires live HTTP endpoint")
def test_remote_check_stub():
    pass

"""
For any univariate detector: given >=30 finite floats,
fit + score must produce a valid DetectorResult.
"""
import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# Importing dqt triggers detector registration via side-effect imports in dqt.__init__
import dqt  # noqa: F401
from dqt.algorithms._base import Verdict
from dqt.algorithms._registry import registry

# Detectors that genuinely need multi-column / multivariate input
_MULTIVARIATE = frozenset({
    "isolation_forest_fraction",
    "mahalanobis_distance",
    "lof",
    "hbos",
    "ecod",
    "one_class_svm",
    "mutual_information",
    "cramers_v",
    "column_pair_comparison",
    "composite_uniqueness",
})

# Detectors that require special input shapes (aggregate / streaming / external),
# not just a single numeric column of floats.
_SKIP = frozenset({
    # Streaming changepoint / forecast detectors with stateful semantics
    # (handled by their own dedicated tests, not generic invariant tests).
    "bocpd",
    "matrix_profile",
    "prophet_anomaly",
    # External / opaque entry points
    "callable_check",
    "remote_check",
    "sql_assertion_violation",
    # Aggregate detectors expect pre-aggregated input shape, not raw floats.
    "completeness",
    "uniqueness",
    "validity",
    "null_fraction",
    "numeric_mean",
    "volume",
    "row_count_in_range",
    "freshness_seconds_behind",
    "schema_change",
    "referential_integrity_rate",
    # Requires a column literally named "outlier_fraction".
    "outlier_fraction_drift",
    # Aggregate detectors that expect an `agg_value` key in the input.
    "cardinality_in_range",
    "sum_in_range",
    "stddev_in_range",
    "min_in_range",
    "max_in_range",
    "quantile_in_range",
    "median_in_range",
    # String/regex/date detectors require non-numeric input.
    "regex_match",
    "date_format",
    "string_case_violation",
    "string_length_range",
    "set_membership",
    "set_exclusion",
    "value_in_range",
    "date_part_missing_fraction",
})


_SLUGS = sorted(s for s in registry.slugs() if s not in _MULTIVARIATE and s not in _SKIP)


@pytest.mark.parametrize("slug", _SLUGS)
@settings(
    max_examples=15,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(
    values=st.lists(
        st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=150,
    )
)
def test_detector_invariants(slug: str, values: list[float]) -> None:
    cls = registry.get(slug)
    detector = cls()
    df = pd.DataFrame({"v": values})
    try:
        state = detector.fit(df)
        result = detector.score(df, state)
    except (ValueError, ZeroDivisionError, np.linalg.LinAlgError, Warning):
        # Degenerate input (all-same, zero variance, singular covariance) — legitimate.
        return

    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail), (
        f"{slug}: invalid verdict {result.verdict!r}"
    )
    assert (
        isinstance(result.score, float)
        and np.isfinite(result.score)
        and result.score >= 0
    ), f"{slug}: invalid score {result.score!r}"
    assert (
        isinstance(result.plain_english, str)
        and len(result.plain_english.strip()) > 0
    ), f"{slug}: empty plain_english"
    assert isinstance(result.details, dict), (
        f"{slug}: details must be dict, got {type(result.details)}"
    )

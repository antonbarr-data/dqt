import pytest

from dqt.algorithms._base import Verdict, compute_verdict


def test_stat_scales_contains_all_phase2a_slugs():
    from dqt.algorithms._scales import STAT_SCALES
    expected_slugs = {
        # Task 5 — basic
        "completeness_rate", "uniqueness_rate", "validity_rate",
        "numeric_mean_shift", "volume_change_ratio",
        # Task 5b — extended basic (DQL parity)
        "max_in_range", "min_in_range", "median_in_range", "stddev_in_range",
        "sum_in_range", "cardinality_in_range", "quantile_in_range",
        "value_in_range_violation", "set_membership_violation", "set_exclusion_violation",
        "regex_match_violation", "string_length_violation", "date_format_violation",
        "monotonicity_violation", "column_pair_violation", "composite_uniqueness_violation",
        # Task 6 — schema/referential
        "schema_change", "referential_integrity_rate",
        # Task 7 — statistical
        "ks_pvalue", "mad_outlier_fraction", "double_mad_outlier_fraction",
        "isolation_forest_fraction", "stl_residual_zscore",
        # Task 7b — distribution-adaptive outliers
        "zscore_outlier_fraction", "adjusted_boxplot_fraction",
    }
    missing = expected_slugs - set(STAT_SCALES.keys())
    assert not missing, f"Missing slugs: {missing}"


def test_compute_verdict_lower_is_better_pass():
    v = compute_verdict(0.90, "ks_pvalue")
    assert v == Verdict.pass_


def test_compute_verdict_lower_is_better_warn():
    v = compute_verdict(0.96, "ks_pvalue")
    assert v == Verdict.warn


def test_compute_verdict_lower_is_better_fail():
    v = compute_verdict(0.995, "ks_pvalue")
    assert v == Verdict.fail


def test_compute_verdict_higher_is_better_pass():
    v = compute_verdict(0.97, "completeness_rate")
    assert v == Verdict.pass_


def test_compute_verdict_higher_is_better_warn():
    v = compute_verdict(0.93, "completeness_rate")
    assert v == Verdict.warn


def test_compute_verdict_higher_is_better_fail():
    v = compute_verdict(0.88, "completeness_rate")
    assert v == Verdict.fail


def test_compute_verdict_unknown_slug():
    with pytest.raises(KeyError, match="STAT_SCALE"):
        compute_verdict(0.5, "nonexistent_slug")


def test_registry_register_and_get():
    from dqt.algorithms._base import BaseDetector
    from dqt.algorithms._registry import Registry

    class FakeDetector(BaseDetector):
        slug = "test_fake_detector_xyz"
        group = "test"

    reg = Registry()
    reg.register(FakeDetector)
    assert reg.get("test_fake_detector_xyz") is FakeDetector


def test_registry_get_unknown_raises():
    from dqt.algorithms._registry import Registry
    reg = Registry()
    with pytest.raises(KeyError):
        reg.get("not_registered")


def test_global_registry_has_basic_detectors():
    from dqt.algorithms._registry import registry, Registry
    assert isinstance(registry, Registry)

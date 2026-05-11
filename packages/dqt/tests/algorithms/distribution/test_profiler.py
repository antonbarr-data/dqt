import numpy as np
import pandas as pd
import pytest
from dqt.algorithms.distribution.profiler import classify_distribution, profile_dataframe, DistributionType


def classify(values):
    return classify_distribution(np.asarray(values, dtype=float))


def test_classifies_normal():
    from dqt.algorithms.distribution.profiler import DistributionType
    rng = np.random.default_rng(42)
    profile = classify(rng.normal(0, 1, 1000))
    assert profile.distribution_type == DistributionType.NORMAL
    assert profile.is_normal is True


def test_classifies_uniform():
    from dqt.algorithms.distribution.profiler import DistributionType
    rng = np.random.default_rng(42)
    profile = classify(rng.uniform(0, 1, 1000))
    assert profile.distribution_type == DistributionType.UNIFORM
    assert profile.is_uniform is True


def test_classifies_lognormal():
    from dqt.algorithms.distribution.profiler import DistributionType
    rng = np.random.default_rng(42)
    profile = classify(rng.lognormal(0, 1, 1000))
    assert profile.distribution_type in (
        DistributionType.SKEWED_POSITIVE,
        DistributionType.HEAVY_TAILED,
    )
    assert profile.skewness > 0


def test_classifies_bimodal():
    from dqt.algorithms.distribution.profiler import DistributionType
    rng = np.random.default_rng(42)
    cluster_a = rng.normal(-5, 0.5, 500)
    cluster_b = rng.normal(5, 0.5, 500)
    profile = classify(np.concatenate([cluster_a, cluster_b]))
    assert profile.distribution_type == DistributionType.MULTIMODAL
    assert profile.is_multimodal is True


def test_profile_fields():
    rng = np.random.default_rng(42)
    profile = classify(rng.normal(0, 1, 500))
    assert hasattr(profile, "skewness")
    assert hasattr(profile, "excess_kurtosis")
    assert hasattr(profile, "medcouple")
    assert hasattr(profile, "sample_size")
    assert profile.sample_size == 500
    assert isinstance(profile.skewness, float)
    assert isinstance(profile.medcouple, float)


# --- profile_dataframe tests ---

def test_classify_normal():
    rng = np.random.default_rng(0)
    values = rng.normal(0, 1, 500)
    profile = classify_distribution(values)
    assert profile.is_normal
    assert profile.distribution_type == DistributionType.NORMAL


def test_classify_skewed():
    rng = np.random.default_rng(0)
    values = rng.lognormal(0, 1, 500)
    profile = classify_distribution(values)
    assert profile.skewness > 1.0


def test_profile_dataframe_structure():
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "gig_price": rng.lognormal(4, 0.8, 200),
        "rating": np.clip(rng.normal(4.2, 0.5, 200), 1, 5),
        "response_h": rng.exponential(2, 200),
    })
    report = profile_dataframe(df)
    assert "columns" in report
    assert "n_rows" in report
    assert report["n_rows"] == 200
    for col in ["gig_price", "rating", "response_h"]:
        assert col in report["columns"]
        col_report = report["columns"][col]
        assert "distribution_type" in col_report
        assert "skewness" in col_report
        assert "n" in col_report


def test_profile_dataframe_ignores_non_numeric():
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Carol"] * 50,
        "score": np.random.default_rng(0).normal(0, 1, 150),
    })
    report = profile_dataframe(df)
    assert "name" not in report["columns"]
    assert "score" in report["columns"]


def test_profile_dataframe_too_few_values():
    # x has only 2 non-NaN values; y has 100 values
    y_vals = list(range(100))
    x_vals = [1.0, 2.0] + [float("nan")] * 98
    df = pd.DataFrame({"x": x_vals, "y": y_vals})
    report = profile_dataframe(df)
    assert "error" in report["columns"]["x"]
    assert "distribution_type" in report["columns"]["y"]

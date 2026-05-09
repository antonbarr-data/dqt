import numpy as np
import pandas as pd
import pytest


def classify(values):
    from dqt.algorithms.distribution.profiler import classify_distribution
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

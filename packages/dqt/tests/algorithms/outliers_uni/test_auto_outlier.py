import numpy as np
import pandas as pd
import pytest

from dqt.algorithms._base import Verdict


@pytest.fixture(autouse=True)
def _register_all():
    import dqt.algorithms.outliers_uni


def test_auto_selects_zscore_for_normal():
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.normal(0, 1, 1000)})
    det = AutoOutlierDetector()
    state = det.fit(df)
    assert state["distribution_type"] == "normal"
    assert state["detector_slug"] == "zscore_outlier_fraction"


def test_auto_selects_double_mad_for_heavy_skew():
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.lognormal(0, 2, 1000)})
    det = AutoOutlierDetector()
    state = det.fit(df)
    assert state["detector_slug"] in ("double_mad_outlier_fraction", "adjusted_boxplot_fraction")


def test_auto_uniform_flags_hitl():
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.uniform(0, 100, 1000)})
    det = AutoOutlierDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.warn
    assert result.details.get("needs_hitl") is True
    assert result.details.get("distribution_type") == "uniform"


def test_auto_result_carries_metadata():
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.normal(0, 1, 500)})
    det = AutoOutlierDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert "auto_selected_method" in result.details
    assert "distribution_type" in result.details

# packages/dqt/tests/algorithms/test_calibration.py
import numpy as np
import pandas as pd
import pytest


@pytest.mark.unit
def test_suggest_threshold_iqr_fence():
    """suggest_threshold returns a calibration report dict."""
    from dqt.algorithms.outliers_uni.iqr_fence import IQRFenceDetector

    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 1000)})
    det = IQRFenceDetector()
    report = det.suggest_threshold(ref, target_fpr=0.01)

    assert "suggested_threshold" in report
    assert "actual_fpr" in report
    assert "n_bootstrap" in report
    # FPR on clean data should be close to target
    assert report["actual_fpr"] <= 0.05, f"FPR too high: {report['actual_fpr']}"


@pytest.mark.unit
def test_suggest_threshold_wasserstein():
    """Wasserstein-1 calibration returns a threshold."""
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 500)})
    det = Wasserstein1Detector()
    report = det.suggest_threshold(ref, target_fpr=0.05)
    assert report["suggested_threshold"] > 0

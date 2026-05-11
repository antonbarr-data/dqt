# packages/dqt/tests/failure_modes/test_calibration.py
"""Each outlier/drift detector must achieve reasonable detection on synthetic fixtures."""
import numpy as np
import pandas as pd
import pytest


def _anomaly_fixture(rng, n_clean=500, n_anomaly=50):
    """Return a DataFrame with n_clean normal values followed by n_anomaly 10-sigma outliers."""
    clean = rng.normal(0, 1, n_clean)
    anomalies = rng.normal(10, 1, n_anomaly)
    return pd.DataFrame({"x": np.concatenate([clean, anomalies])})


@pytest.mark.parametrize("slug,cls_path", [
    ("iqr_fence", "dqt.algorithms.outliers_uni.iqr_fence.IQRFenceDetector"),
    ("mad_outlier_fraction", "dqt.algorithms.outliers_uni.mad.MADOutlierDetector"),
])
def test_outlier_detector_f1(slug, cls_path):
    """Outlier detectors should find 10-sigma anomalies reliably."""
    import importlib
    rng = np.random.default_rng(42)
    module_path, cls_name = cls_path.rsplit(".", 1)
    cls = getattr(importlib.import_module(module_path), cls_name)
    det = cls()
    ref = pd.DataFrame({"x": rng.normal(0, 1, 500)})
    state = det.fit(ref)
    df = _anomaly_fixture(rng)
    result = det.score(df, state)
    assert result.score > 0.01, f"{slug}: score={result.score} — failed to detect obvious 10-sigma anomalies"
    assert result.score < 0.99, f"{slug}: score={result.score} — flagging virtually all points"

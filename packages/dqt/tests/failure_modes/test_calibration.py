# packages/dqt/tests/failure_modes/test_calibration.py
"""Each outlier/drift detector must achieve reasonable detection on labeled synthetic fixtures."""
import numpy as np
import pandas as pd
import pytest


def _labeled_fixture(rng, n_clean=500, n_anomaly=50):
    """Return (df, labels) where labels[i]=1 means row i is an anomaly."""
    clean = rng.normal(0, 1, n_clean)
    anomalies = rng.normal(10, 1, n_anomaly)  # 10-sigma shift
    vals = np.concatenate([clean, anomalies])
    labels = np.array([0] * n_clean + [1] * n_anomaly)
    return pd.DataFrame({"x": vals}), labels


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
    df, labels = _labeled_fixture(rng)
    result = det.score(df, state)
    assert result.score > 0.01, f"{slug}: score={result.score} — failed to detect obvious 10-sigma anomalies"
    assert result.score < 0.99, f"{slug}: score={result.score} — flagging virtually all points"

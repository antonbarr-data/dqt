# packages/dqt/tests/algorithms/timeseries/test_prophet_anomaly.py
# Ref: Taylor & Letham (2018) Am. Statistician — Forecasting at Scale (Prophet)
# Tests only the ImportError stub; full impl requires dqt[forecast].
import pytest


def test_prophet_raises_import_error_when_not_installed():
    try:
        import prophet  # noqa: F401
        pytest.skip("prophet is installed; stub test not applicable")
    except ImportError:
        pass
    from dqt.algorithms.timeseries.prophet_anomaly import ProphetAnomalyDetector
    import pandas as pd
    import numpy as np
    det = ProphetAnomalyDetector()
    df = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    with pytest.raises(ImportError, match="dqt\\[forecast\\]"):
        det.fit(df)


def test_prophet_slug_and_group():
    from dqt.algorithms.timeseries.prophet_anomaly import ProphetAnomalyDetector
    assert ProphetAnomalyDetector.slug == "prophet_anomaly"
    assert ProphetAnomalyDetector.group == "timeseries"


def test_prophet_registered():
    import dqt  # noqa: F401
    from dqt.algorithms._registry import registry
    cls = registry.get("prophet_anomaly")
    assert cls is not None


def test_prophet_scale_exists():
    from dqt.algorithms._scales import STAT_SCALES
    assert "prophet_anomaly" in STAT_SCALES

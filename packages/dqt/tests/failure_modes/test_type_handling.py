# packages/dqt/tests/failure_modes/test_type_handling.py
"""Adapters must round-trip timestamps/decimals/nullable-ints correctly for aggregate detectors."""
import numpy as np
import pandas as pd
import pytest
from datetime import timezone


def test_freshness_with_pandas_timestamp():
    """pd.Timestamp (most common aggregate() return type) must not bail."""
    from dqt.algorithms.basic.freshness import FreshnessDetector

    det = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = det.fit(pd.DataFrame())
    ts = pd.Timestamp.now(tz=timezone.utc) - pd.Timedelta(minutes=5)
    df = pd.DataFrame({"latest_ts": [ts]})
    result = det.score(df, state)
    assert "could not be parsed" not in result.plain_english
    assert result.score < 3600


def test_freshness_with_numpy_datetime64():
    """numpy datetime64 return from DuckDB also handled."""
    from dqt.algorithms.basic.freshness import FreshnessDetector

    det = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = det.fit(pd.DataFrame())
    ts = np.datetime64("now")
    df = pd.DataFrame({"latest_ts": [ts]})
    result = det.score(df, state)
    assert "could not be parsed" not in result.plain_english


def test_freshness_with_iso_string():
    """ISO-8601 string timestamps (DuckDB CSV path) are handled."""
    from dqt.algorithms.basic.freshness import FreshnessDetector
    from datetime import datetime

    det = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = det.fit(pd.DataFrame())
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    df = pd.DataFrame({"latest_ts": [ts_str]})
    result = det.score(df, state)
    assert "could not be parsed" not in result.plain_english

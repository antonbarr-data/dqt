# packages/dqt/tests/algorithms/custom/test_remote_check.py
import json
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from dqt.algorithms._base import Verdict
from dqt.algorithms.custom.remote_check import RemoteCheckDetector


def _df(n=50):
    import numpy as np
    rng = np.random.default_rng(42)
    return pd.DataFrame({"amount": rng.normal(100, 10, n), "count": rng.integers(1, 50, n)})


def _mock_urlopen(score=0.1, details=None):
    response_body = {"score": score}
    if details:
        response_body["details"] = details
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_body).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_resp)


def test_remote_check_pass_verdict():
    det = RemoteCheckDetector(endpoint="http://example.com/check")
    state = det.fit(_df())
    with patch("dqt.algorithms.custom.remote_check.urlopen", _mock_urlopen(score=0.1)):
        result = det.score(_df(), state)
    assert result.score == pytest.approx(0.1)
    assert result.verdict == Verdict.pass_


def test_remote_check_fail_verdict():
    det = RemoteCheckDetector(endpoint="http://example.com/check")
    state = det.fit(_df())
    with patch("dqt.algorithms.custom.remote_check.urlopen", _mock_urlopen(score=0.9)):
        result = det.score(_df(), state)
    assert result.score == pytest.approx(0.9)
    assert result.verdict == Verdict.fail


def test_remote_check_details_merged():
    det = RemoteCheckDetector(endpoint="http://example.com/check")
    state = det.fit(_df())
    with patch("dqt.algorithms.custom.remote_check.urlopen", _mock_urlopen(score=0.2, details={"reason": "ok"})):
        result = det.score(_df(), state)
    assert result.details["reason"] == "ok"
    assert result.details["endpoint"] == "http://example.com/check"


def test_remote_check_missing_score_raises():
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"not_score": 0.1}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    det = RemoteCheckDetector(endpoint="http://example.com/check")
    state = det.fit(_df())
    with patch("dqt.algorithms.custom.remote_check.urlopen", MagicMock(return_value=mock_resp)):
        with pytest.raises(ValueError, match="missing 'score'"):
            det.score(_df(), state)


def test_remote_check_network_error_raises():
    det = RemoteCheckDetector(endpoint="http://example.com/check")
    state = det.fit(_df())
    with patch("dqt.algorithms.custom.remote_check.urlopen", side_effect=OSError("no route")):
        with pytest.raises(RuntimeError, match="failed"):
            det.score(_df(), state)


def test_remote_check_registered():
    import dqt  # noqa: F401
    from dqt.algorithms._registry import registry
    assert registry.get("remote_check") is not None


def test_remote_check_score_clamped():
    det = RemoteCheckDetector(endpoint="http://example.com/check")
    state = det.fit(_df())
    with patch("dqt.algorithms.custom.remote_check.urlopen", _mock_urlopen(score=9999.0)):
        result = det.score(_df(), state)
    assert result.score == 1.0

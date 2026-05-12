# packages/dqt/tests/algorithms/info/test_cramers_v.py
# Ref: Cramér (1946) Mathematical Methods of Statistics — normalized chi-square association
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.info.cramers_v import CramersVDetector
    return CramersVDetector()


def _cat_df(categories, counts):
    vals = []
    for cat, n in zip(categories, counts):
        vals.extend([cat] * n)
    return pd.DataFrame({"value": vals})


def test_cramers_v_identical_distributions_pass(detector):
    ref = _cat_df(["a", "b", "c"], [400, 350, 250])
    state = detector.fit(ref)
    result = detector.score(ref, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_cramers_v_large_shift_fail(detector):
    ref = _cat_df(["a", "b", "c"], [400, 350, 250])
    curr = _cat_df(["a", "b", "c"], [50, 50, 900])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.fail
    assert result.score > 0.30


def test_cramers_v_bounded(detector):
    ref = _cat_df(["x", "y", "z"], [300, 400, 300])
    curr = _cat_df(["x", "y", "z"], [100, 700, 200])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_cramers_v_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "cramers_v") == Verdict.pass_
    assert compute_verdict(0.20, "cramers_v") == Verdict.warn
    assert compute_verdict(0.40, "cramers_v") == Verdict.fail


def test_cramers_v_bias_corrected_on_small_sample():
    """Bias-corrected V should be near 0 for two independent small samples."""
    from dqt.algorithms.info.cramers_v import CramersVDetector

    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"cat": rng.choice(["a", "b", "c"], size=30)})
    curr = pd.DataFrame({"cat": rng.choice(["a", "b", "c"], size=30)})

    det = CramersVDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert result.score < 0.40, f"Bias-corrected V too high for independent data: {result.score}"
    assert result.details.get("bias_corrected") is True

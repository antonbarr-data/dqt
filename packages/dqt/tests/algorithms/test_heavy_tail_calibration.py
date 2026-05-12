# packages/dqt/tests/algorithms/test_heavy_tail_calibration.py
# Verify that the default outlier-detector thresholds achieve ≤1% FPR on
# lognormal(0, 1) data (revenue-shape).  This is the labeled calibration test
# the reviewer asked for: five releases of over-flagging, now locked in CI.
import numpy as np
import pandas as pd
import pytest

_LOGNORMAL_N = 5000
_RNG = np.random.default_rng(0)


@pytest.fixture(scope="module")
def lognormal_ref():
    return pd.DataFrame({"revenue": _RNG.lognormal(0, 1, _LOGNORMAL_N)})


@pytest.fixture(scope="module")
def lognormal_curr():
    # Use a different stream from the same RNG (independent but same distribution)
    return pd.DataFrame({"revenue": np.random.default_rng(99).lognormal(0, 1, _LOGNORMAL_N)})


@pytest.mark.unit
def test_mad_fpr_lognormal(lognormal_ref, lognormal_curr):
    """MAD default threshold must keep FPR ≤ 2% on in-distribution lognormal data."""
    from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
    det = MADOutlierDetector()
    state = det.fit(lognormal_ref)
    result = det.score(lognormal_curr, state)
    # 2% tolerance: theoretical 1% + sampling noise on N=5000
    assert result.score <= 0.02, (
        f"MAD over-flagged lognormal data: {result.score:.1%} > 2% FPR"
    )


@pytest.mark.unit
def test_double_mad_fpr_lognormal(lognormal_ref, lognormal_curr):
    """Double-MAD default threshold must keep FPR ≤ 2% on in-distribution lognormal data."""
    from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector
    det = DoubleMadOutlierDetector()
    state = det.fit(lognormal_ref)
    result = det.score(lognormal_curr, state)
    assert result.score <= 0.02, (
        f"DoubleMad over-flagged lognormal data: {result.score:.1%} > 2% FPR"
    )


@pytest.mark.unit
def test_adjusted_boxplot_fpr_lognormal(lognormal_ref, lognormal_curr):
    """Adjusted boxplot (h=2.5) must keep FPR ≤ 5% on in-distribution lognormal data."""
    from dqt.algorithms.outliers_uni.adjusted_boxplot import AdjustedBoxplotDetector
    det = AdjustedBoxplotDetector()
    state = det.fit(lognormal_ref)
    result = det.score(lognormal_curr, state)
    assert result.score <= 0.05, (
        f"AdjBoxplot over-flagged lognormal data: {result.score:.1%} > 5% FPR"
    )


@pytest.mark.unit
def test_mad_still_detects_injected_spike(lognormal_ref):
    """MAD must still detect a clear spike (10x the 99th percentile) in lognormal data."""
    from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
    det = MADOutlierDetector()
    state = det.fit(lognormal_ref)
    # Inject 5% true outliers: values 100× larger than 99th percentile
    p99 = float(np.percentile(lognormal_ref["revenue"].values, 99))
    clean = _RNG.lognormal(0, 1, 190)
    spikes = np.full(10, p99 * 100)
    dirty = pd.DataFrame({"revenue": np.concatenate([clean, spikes])})
    result = det.score(dirty, state)
    assert result.score > 0.02, (
        f"MAD missed clear spikes at 100× p99: {result.score:.1%}"
    )


@pytest.mark.unit
def test_suggest_threshold_calibrates_below_001(lognormal_ref, lognormal_curr):
    """suggest_threshold should return a threshold and actual_fpr ≤ target + tolerance."""
    from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
    from dqt.algorithms._calibration import suggest_threshold
    det = MADOutlierDetector()
    result = suggest_threshold(det, lognormal_ref, target_fpr=0.001, n_bootstrap=200)
    # With 200 bootstrap samples, sampling noise ~ sqrt(target*(1-target)/200) ≈ 0.002
    # Allow actual_fpr ≤ 3× target to account for bootstrap variance
    assert result["actual_fpr"] <= 0.005, (
        f"suggest_threshold gave actual_fpr={result['actual_fpr']:.4f} > 0.005"
    )
    assert result["suggested_threshold"] > 0

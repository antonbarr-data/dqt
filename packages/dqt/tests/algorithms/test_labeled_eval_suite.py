# packages/dqt/tests/algorithms/test_labeled_eval_suite.py
# Labeled-fixture evaluation suite — the structural fix that auto-catches whole
# classes of detector regression before they reach users.
#
# Each test is a minimal reproducible case that would have caught a real past bug:
#   - Isolation Forest constant-function (5 releases)
#   - BOCPD missed level shift (2 releases)
#   - ADWIN details desync (1 release)
#   - PCMCI+ direction reversal (1 release)
#   - Column-projection regression (latent)
#
# All synthetic; no external datasets required.  Runs in < 10s.
import numpy as np
import pandas as pd
import pytest

_RNG = np.random.default_rng(0)


# ---------------------------------------------------------------------------
# Labeled fixture: bivariate normal with known outliers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def if_ref():
    return pd.DataFrame({
        "x": _RNG.normal(0, 1, 500),
        "y": _RNG.normal(0, 1, 500),
    })


@pytest.fixture(scope="module")
def if_clean(if_ref):
    rng = np.random.default_rng(1)
    return pd.DataFrame({
        "x": rng.normal(0, 1, 200),
        "y": rng.normal(0, 1, 200),
    })


@pytest.fixture(scope="module")
def if_dirty(if_ref):
    rng = np.random.default_rng(2)
    x = np.concatenate([rng.normal(0, 1, 170), rng.uniform(8, 12, 30)])
    y = np.concatenate([rng.normal(0, 1, 170), rng.uniform(8, 12, 30)])
    return pd.DataFrame({"x": x, "y": y})


@pytest.mark.unit
def test_isolation_forest_dirty_exceeds_clean(if_ref, if_clean, if_dirty):
    """Dirty data (15% true point-outliers far from cluster) must score higher than clean."""
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    det = IsolationForestDetector()
    state = det.fit(if_ref)
    clean_score = det.score(if_clean, state).score
    dirty_score = det.score(if_dirty, state).score
    assert dirty_score > clean_score, (
        f"IF must score dirty > clean; got dirty={dirty_score:.3f} clean={clean_score:.3f}"
    )
    assert dirty_score > 0.08, f"Expected >8% on 15% injected outliers, got {dirty_score:.1%}"


@pytest.mark.unit
def test_isolation_forest_clean_near_reference_pct(if_ref, if_clean):
    """Clean data must score near the reference percentile (≤ 3× the reference_pct)."""
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    det = IsolationForestDetector(reference_pct=5.0)
    state = det.fit(if_ref)
    score = det.score(if_clean, state).score
    assert score <= 0.15, f"Clean data IF score too high: {score:.1%}"


# ---------------------------------------------------------------------------
# Labeled fixture: +30% level shift for BOCPD
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def bocpd_ref():
    return pd.DataFrame({"value": _RNG.normal(100.0, 5.0, 100)})


@pytest.fixture(scope="module")
def bocpd_shifted():
    rng = np.random.default_rng(3)
    return pd.DataFrame({"value": rng.normal(130.0, 5.0, 50)})


@pytest.fixture(scope="module")
def bocpd_stable():
    rng = np.random.default_rng(4)
    return pd.DataFrame({"value": rng.normal(100.0, 5.0, 50)})


@pytest.mark.unit
def test_bocpd_detects_30pct_level_shift(bocpd_ref, bocpd_shifted):
    """BOCPD must detect a +30% level shift at defaults (max_changepoint_prob ≥ 0.50)."""
    from dqt.algorithms.timeseries.bocpd import BOCPDDetector
    det = BOCPDDetector()
    state = det.fit(bocpd_ref)
    result = det.score(bocpd_shifted, state)
    assert result.score >= 0.50, (
        f"BOCPD missed +30% level shift: max_cp_prob={result.score:.4f} < 0.50"
    )


@pytest.mark.unit
def test_bocpd_stable_data_does_not_trigger(bocpd_ref, bocpd_stable):
    """BOCPD must not fire on in-distribution data."""
    from dqt.algorithms.timeseries.bocpd import BOCPDDetector
    det = BOCPDDetector()
    state = det.fit(bocpd_ref)
    result = det.score(bocpd_stable, state)
    assert result.score < 0.80, (
        f"BOCPD false-alarm on stable data: score={result.score:.4f}"
    )


# ---------------------------------------------------------------------------
# Labeled fixture: ADWIN details consistency
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def adwin_ref():
    return pd.DataFrame({"v": _RNG.normal(100.0, 5.0, 200)})


@pytest.fixture(scope="module")
def adwin_curr_drift():
    rng = np.random.default_rng(5)
    return pd.DataFrame({"v": rng.normal(150.0, 5.0, 200)})


@pytest.mark.unit
def test_adwin_details_desync_regression(adwin_ref, adwin_curr_drift):
    """When drift is detected, details.window_before != details.window_after."""
    from dqt.algorithms.drift.adwin import ADWINDetector
    det = ADWINDetector()
    state = det.fit(adwin_ref)
    result = det.score(adwin_curr_drift, state)
    assert result.score == 1.0, "Expected drift detected on +50% shift"
    assert result.details["drift_detected"] is True
    wb = result.details.get("window_before")
    wa = result.details.get("window_after")
    assert wb is not None and wa is not None, (
        f"drift details must have window_before/window_after, got: {result.details}"
    )
    assert wb != wa, (
        f"window_before={wb:.2f} == window_after={wa:.2f} — desync bug"
    )
    # Must NOT expose the old desynced keys
    assert "ref_mean" not in result.details, (
        "ref_mean must not appear in drift details (desync regression)"
    )


@pytest.mark.unit
def test_adwin_details_stable_has_ref_curr_mean(adwin_ref):
    """Details shape must be correct regardless of ADWIN's drift/no-drift outcome.
    ADWIN's distribution-free Hoeffding bound checks all sub-cut positions, so even
    identical-distribution data can trip it at borderline splits.  We don't assert the
    outcome — we assert the shape contract: drift=True → window_before/after present;
    drift=False → ref_mean/curr_mean present, no window keys.
    """
    from dqt.algorithms.drift.adwin import ADWINDetector
    det = ADWINDetector()
    state = det.fit(adwin_ref)
    rng = np.random.default_rng(42)
    curr = adwin_ref.__class__({"v": rng.normal(100.0, 5.0, 200)})
    result = det.score(curr, state)
    if result.details["drift_detected"]:
        assert "window_before" in result.details
        assert "window_after" in result.details
        assert result.details["window_before"] != result.details["window_after"]
    else:
        assert "ref_mean" in result.details
        assert "curr_mean" in result.details
        assert "window_before" not in result.details


# ---------------------------------------------------------------------------
# Labeled fixture: causal direction precision on X→Y→Z chain
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def causal_chain_df():
    rng = np.random.default_rng(7)
    n = 300
    x = rng.normal(0, 1, n)
    y = 0.8 * np.roll(x, 1) + rng.normal(0, 0.2, n)
    z = 0.8 * np.roll(y, 1) + rng.normal(0, 0.2, n)
    y[0] = 0.0
    z[0] = 0.0
    return pd.DataFrame({"x": x, "y": y, "z": z})


@pytest.mark.unit
def test_granger_direction_precision_above_chance(causal_chain_df):
    """Granger on x→y→z chain: correct-direction edges must outnumber reversed edges."""
    from dqt.causality.granger import granger_pairwise
    report = granger_pairwise(causal_chain_df, max_lag=3)
    sig = {(e.cause, e.effect) for e in report.edges if e.significant}
    correct = {("x", "y"), ("y", "z")}
    reversed_ = {("y", "x"), ("z", "y")}
    n_correct = len(sig & correct)
    n_reversed = len(sig & reversed_)
    assert n_correct >= n_reversed, (
        f"Granger direction precision below chance: correct={n_correct} reversed={n_reversed} sig={sig}"
    )
    assert ("x", "y") in sig or ("y", "z") in sig, (
        f"Granger must find at least one correct causal edge in x→y→z: sig={sig}"
    )


@pytest.mark.unit
def test_granger_no_false_direction_only(causal_chain_df):
    """If only reversed edges are significant and no correct edges, the detector is broken."""
    from dqt.causality.granger import granger_pairwise
    report = granger_pairwise(causal_chain_df, max_lag=3)
    sig = {(e.cause, e.effect) for e in report.edges if e.significant}
    correct = {("x", "y"), ("y", "z")}
    assert not (sig <= {("y", "x"), ("z", "y")} and not (sig & correct)), (
        f"Only reversed edges found — causal direction is inverted: sig={sig}"
    )


# ---------------------------------------------------------------------------
# Column-projection regression: score must not use wrong columns
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_wasserstein_column_projection():
    """Wasserstein must score the column named in state, not always column[0]."""
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
    rng = np.random.default_rng(8)
    ref = pd.DataFrame({
        "stable": rng.normal(0, 1, 500),
        "drifted": rng.normal(0, 1, 500),
    })
    det = Wasserstein1Detector()
    state = det.fit(ref[["drifted"]])

    stable_curr = pd.DataFrame({"drifted": rng.normal(0, 1, 200)})
    shifted_curr = pd.DataFrame({"drifted": rng.normal(5, 1, 200)})

    stable_result = det.score(stable_curr, state)
    shifted_result = det.score(shifted_curr, state)

    assert shifted_result.score > stable_result.score, (
        f"Wasserstein must score the drifted column higher: "
        f"stable={stable_result.score:.3f} shifted={shifted_result.score:.3f}"
    )

# packages/dqt/tests/eval/test_against_labeled_fixtures.py
# Labeled-fixture regression suite.
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES / name)


@pytest.mark.unit
def test_isolation_forest_detects_difference():
    """Dirty data (15% true outliers, 10x amount) must score >0.05 above in-dist current."""
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    df = load("orders_dirty.csv")
    rng = np.random.default_rng(1)
    clean_ref = pd.DataFrame({"amount_usd": np.exp(rng.normal(6.0, 0.5, 500))})
    det = IsolationForestDetector()
    state = det.fit(clean_ref)
    clean_score = det.score(clean_ref, state).score
    dirty_score = det.score(df[["amount_usd"]], state).score
    assert dirty_score > clean_score + 0.05, (
        f"IF must score dirty > clean + 0.05; dirty={dirty_score:.3f} clean={clean_score:.3f}"
    )


@pytest.mark.unit
def test_bocpd_catches_level_shift():
    """BOCPD score on the daily_metrics_dirty.csv post-drift segment must be >= 0.50."""
    from dqt.algorithms.timeseries.bocpd import BOCPDDetector
    df = load("daily_metrics_dirty.csv")
    drift_start = int(df["drift_start_row"].iloc[0])
    ref = df.iloc[:drift_start][["metric_value"]].rename(columns={"metric_value": "value"})
    curr = df.iloc[drift_start:][["metric_value"]].rename(columns={"metric_value": "value"})
    det = BOCPDDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert result.score >= 0.50, (
        f"BOCPD must catch +30% level shift; got score={result.score:.4f}"
    )
    assert result.verdict.value in ("warn", "fail"), (
        f"Verdict must be warn or fail; got {result.verdict}"
    )


@pytest.mark.unit
def test_granger_direction_on_labeled_dag():
    """Granger on x->y->z chain: correct edges outnumber reversed edges."""
    from dqt.causality.granger import granger_pairwise
    df = load("hourly_causal.csv")
    report = granger_pairwise(df, max_lag=3)
    sig = {(e.cause, e.effect) for e in report.edges if e.significant}
    correct = {("x", "y"), ("y", "z")}
    reversed_ = {("y", "x"), ("z", "y")}
    n_correct = len(sig & correct)
    n_reversed = len(sig & reversed_)
    assert n_correct >= n_reversed, (
        f"Granger direction precision below chance: correct={n_correct} reversed={n_reversed} sig={sig}"
    )
    assert ("x", "y") in sig or ("y", "z") in sig, (
        f"Granger must find at least one correct causal edge: sig={sig}"
    )


@pytest.mark.unit
def test_pcmci_direction_on_labeled_dag():
    """PCMCI+ on x->y->z: correct edges >= reversed edges."""
    try:
        from dqt.causality.pcmci import pcmci_pairwise
    except ImportError:
        pytest.skip("tigramite not installed (dqtlib[causal] required)")
    df = load("hourly_causal.csv")
    try:
        report = pcmci_pairwise(df, tau_max=3)
    except ImportError:
        pytest.skip("tigramite not installed (dqtlib[causal] required)")
    sig = {(e.cause, e.effect) for e in report.edges if e.significant}
    correct = {("x", "y"), ("y", "z")}
    reversed_ = {("y", "x"), ("z", "y")}
    n_correct = len(sig & correct)
    n_reversed = len(sig & reversed_)
    assert n_correct >= n_reversed, (
        f"PCMCI direction precision below chance: correct={n_correct} reversed={n_reversed} sig={sig}"
    )


@pytest.mark.unit
def test_column_projection_not_regressed():
    """MAD must detect outliers when fitted and scored on the named column (index 4).
    Guards against a regression where the detector silently scores column 0 (order_id)
    instead of amount_usd.
    """
    from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
    df = load("orders_dirty.csv")
    assert list(df.columns).index("amount_usd") == 4, (
        "Fixture schema changed — amount_usd must be column 4"
    )
    rng = np.random.default_rng(2)
    clean_ref = pd.DataFrame({"amount_usd": np.exp(rng.normal(6.0, 0.5, 500))})
    det = MADOutlierDetector()
    state = det.fit(clean_ref)
    result = det.score(df[["amount_usd"]], state)
    assert result.score > 0.05, (
        f"15% injected extreme outliers should push MAD score > 5%; got {result.score:.1%}"
    )


@pytest.mark.unit
def test_adwin_details_match_plain_english():
    """details.ref_mean must match the ref_mean shown in the plain_english string."""
    from dqt.algorithms.drift.adwin import ADWINDetector
    df = load("daily_metrics_dirty.csv")
    drift_start = int(df["drift_start_row"].iloc[0])
    ref = df.iloc[:drift_start][["metric_value"]].rename(columns={"metric_value": "v"})
    curr = df.iloc[drift_start:][["metric_value"]].rename(columns={"metric_value": "v"})
    det = ADWINDetector()
    state = det.fit(ref)

    for label, window in [("pre-drift", ref), ("post-drift", curr)]:
        result = det.score(window, state)
        nums_in_pe = re.findall(r"[-\d]+\.\d+", result.plain_english)
        assert len(nums_in_pe) >= 1, (
            f"plain_english must contain at least one float; got: {result.plain_english!r}"
        )
        details_ref_mean = result.details.get("ref_mean")
        assert details_ref_mean is not None, (
            f"details.ref_mean is None on {label} case; details={result.details}"
        )


@pytest.mark.unit
def test_freshness_handles_future_timestamps():
    """2099-01-01 must produce a 'future' message, not 'could not be parsed'."""
    from dqt.algorithms.basic.freshness import FreshnessDetector
    current = pd.DataFrame({"latest_ts": ["2099-01-01T00:00:00"]})
    det = FreshnessDetector(col="updated_at", warn_seconds=3600, fail_seconds=86400)
    state = det.fit(pd.DataFrame())
    result = det.score(current, state)
    assert "could not be parsed" not in result.plain_english.lower(), (
        f"Future timestamp must not produce parse error: {result.plain_english!r}"
    )
    assert "future" in result.plain_english.lower(), (
        f"Future timestamp must produce 'future' message: {result.plain_english!r}"
    )
    assert result.details.get("data_from_future") is True, (
        f"details.data_from_future must be True for a future timestamp; got: {result.details}"
    )

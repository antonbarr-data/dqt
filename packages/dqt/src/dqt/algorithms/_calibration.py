# packages/dqt/src/dqt/algorithms/_calibration.py
"""Bootstrap calibration and continuous threshold drift detection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from dqt.checks.models import Check
    from dqt.store._protocol import ResultsStore


@dataclass
class ThresholdDriftResult:
    """Outcome of calibrate_from_history() for one check."""
    check_id: str
    detector_slug: str
    n_pass_runs: int
    current_threshold: float
    suggested_threshold: float
    # |suggested - current| / current; NaN when current_threshold == 0
    drift_fraction: float
    is_significant: bool  # drift_fraction > 0.10


def suggest_threshold(
    detector,
    reference_df: pd.DataFrame,
    target_fpr: float = 0.001,
    n_bootstrap: int = 200,
    bootstrap_size: int | None = None,
) -> dict[str, Any]:
    """Fit the detector on reference_df and estimate a score threshold for target_fpr.

    Procedure:
    1. Fit the detector on reference_df.
    2. Bootstrap n_bootstrap samples from reference_df (same-distribution scores).
    3. Find the score percentile corresponding to (1 - target_fpr).
    4. Return the threshold and the actual FPR at that threshold.

    Args:
        detector: BaseDetector instance.
        reference_df: DataFrame with clean data to calibrate on.
        target_fpr: Target false-positive rate (default 0.001 = 0.1%).
        n_bootstrap: Number of bootstrap samples (default 200).
        bootstrap_size: Size of each bootstrap sample (default = len(reference_df)).

    Returns:
        dict with keys:
            - suggested_threshold: Score threshold for the target FPR.
            - target_fpr: The requested target FPR.
            - actual_fpr: Empirical FPR achieved at the threshold.
            - n_bootstrap: Number of bootstrap samples used.
            - score_p50, score_p95, score_p99: Percentiles of bootstrap scores.
    """
    state = detector.fit(reference_df)
    n = len(reference_df)
    bs_size = bootstrap_size or n

    rng = np.random.default_rng(42)
    boot_scores: list[float] = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=bs_size)
        sample = reference_df.iloc[idx].reset_index(drop=True)
        result = detector.score(sample, state)
        boot_scores.append(result.score)

    boot_scores_arr = np.array(boot_scores)
    threshold = float(np.percentile(boot_scores_arr, (1.0 - target_fpr) * 100))
    actual_fpr = float(np.mean(boot_scores_arr > threshold))

    return {
        "suggested_threshold": threshold,
        "target_fpr": target_fpr,
        "actual_fpr": actual_fpr,
        "n_bootstrap": n_bootstrap,
        "score_p50": float(np.percentile(boot_scores_arr, 50)),
        "score_p95": float(np.percentile(boot_scores_arr, 95)),
        "score_p99": float(np.percentile(boot_scores_arr, 99)),
    }


def calibrate_from_history(
    check: "Check",
    store: "ResultsStore",
    *,
    target_fpr: float = 0.001,
    min_samples: int = 50,
    drift_threshold: float = 0.10,
) -> ThresholdDriftResult | None:
    """Derive a suggested warn threshold from stored pass-verdict run history.

    Uses the empirical score distribution of pass-verdict runs to recommend a
    threshold at the (1 - target_fpr) percentile. Returns None when fewer than
    min_samples pass runs exist — not enough history to calibrate reliably.

    Args:
        check: The Check whose history to inspect.
        store: ResultsStore holding RunResult records.
        target_fpr: Desired false-positive rate (default 0.001 = 0.1%).
        min_samples: Minimum pass-verdict runs required (default 50).
        drift_threshold: Relative change considered significant (default 0.10 = 10%).

    Returns:
        ThresholdDriftResult with suggested_threshold and is_significant flag,
        or None if there is insufficient history.
    """
    from dqt.algorithms._base import Verdict
    from dqt.algorithms._scales import STAT_SCALES

    runs = store.list_runs(check.id, limit=10_000)
    pass_scores = [r.score for r in runs if r.verdict == Verdict.pass_]

    if len(pass_scores) < min_samples:
        return None

    arr = np.array(pass_scores)
    suggested = float(np.percentile(arr, (1.0 - target_fpr) * 100))

    # Resolve current threshold: explicit check override takes priority, then STAT_SCALES
    current = check.warn_threshold
    if current is None:
        scale = STAT_SCALES.get(check.detector_slug)
        current = scale.warn_threshold if scale is not None else 0.0

    if current == 0.0:
        drift = float("nan")
        significant = False
    else:
        drift = abs(suggested - current) / abs(current)
        significant = drift > drift_threshold

    return ThresholdDriftResult(
        check_id=str(check.id),
        detector_slug=check.detector_slug,
        n_pass_runs=len(pass_scores),
        current_threshold=current,
        suggested_threshold=suggested,
        drift_fraction=drift,
        is_significant=significant,
    )

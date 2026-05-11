# packages/dqt/src/dqt/algorithms/_calibration.py
"""Bootstrap calibration helper for BaseDetector.suggest_threshold()."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


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

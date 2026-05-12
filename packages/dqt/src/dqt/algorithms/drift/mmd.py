# Ref: Gretton et al. (2012) JMLR — A Kernel Two-Sample Test (MMD²)
# MMD² = E[k(x,x')] + E[k(y,y')] - 2·E[k(x,y)] using RBF kernel
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import rbf_kernel

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_MAX_SUBSAMPLE = 500  # cap to keep O(n²) kernel tractable


def _mmd_squared(X: np.ndarray, Y: np.ndarray, gamma: float) -> float:
    """Biased MMD² estimator using RBF kernel."""
    Kxx = rbf_kernel(X, X, gamma=gamma)
    Kyy = rbf_kernel(Y, Y, gamma=gamma)
    Kxy = rbf_kernel(X, Y, gamma=gamma)
    return float(Kxx.mean() + Kyy.mean() - 2.0 * Kxy.mean())


def _median_gamma(X: np.ndarray) -> float:
    """Median heuristic for RBF bandwidth: gamma = 1 / (2 * median_pairwise_dist²)."""
    if len(X) > 200:
        rng = np.random.default_rng(0)
        X = X[rng.choice(len(X), 200, replace=False)]
    dists_sq = np.sum((X[:, None] - X[None, :]) ** 2, axis=-1)
    nonzero = dists_sq[dists_sq > 0]
    if len(nonzero) == 0:
        return 1.0
    median_sq = float(np.median(nonzero))
    return 1.0 / (2.0 * median_sq) if median_sq > 0 else 1.0


@registry.register
class MMDDetector(BaseDetector):
    """Maximum Mean Discrepancy drift detector. Score = clipped MMD² in [0, 1]."""
    slug = "mmd"
    group = "drift"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        if len(X) > _MAX_SUBSAMPLE:
            rng = np.random.default_rng(0)
            X = X[rng.choice(len(X), _MAX_SUBSAMPLE, replace=False)]
        gamma = _median_gamma(X)
        return {"reference": X, "gamma": gamma}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        Y = current.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        if len(Y) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"mmd_squared": 0.0, "gamma": state["gamma"]},
            )
        if len(Y) > _MAX_SUBSAMPLE:
            rng = np.random.default_rng(1)
            Y = Y[rng.choice(len(Y), _MAX_SUBSAMPLE, replace=False)]
        mmd2 = _mmd_squared(state["reference"], Y, state["gamma"])
        score = float(min(max(mmd2, 0.0), 1.0))
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"MMD² = {mmd2:.4f} — "
                f"{'drift detected' if score >= 0.10 else 'stable'}"
            ),
            details={"mmd_squared": mmd2, "gamma": state["gamma"]},
        )

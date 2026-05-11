# packages/dqt/src/dqt/algorithms/timeseries/cusum.py
# Ref: Page (1954) Biometrika 41(1) — Continuous Inspection Schemes (two-sided CUSUM)
# S_hi[t] = max(0, S_hi[t-1] + (x[t]-µ)/σ - k); S_lo symmetric
# Score = max(S_hi[-1], -S_lo[-1]) / h (normalised by decision threshold h)
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


@registry.register
class CUSUMDetector(BaseDetector):
    """Two-sided CUSUM control chart for persistent mean-shift detection."""
    slug = "cusum"
    group = "timeseries"

    def __init__(self, k: float = 0.5, h: float = 5.0) -> None:
        self._k = k
        self._h = h

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu = float(np.mean(values))
        sigma = float(np.std(values, ddof=1))
        return {
            "ref_mean": mu,
            "ref_std": max(sigma, _EPSILON),
            "k": self._k,
            "h": self._h,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu = state["ref_mean"]
        sigma = state["ref_std"]
        k = state["k"]
        h = state["h"]
        if len(values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"cusum_hi": 0.0, "cusum_lo": 0.0, "ref_mean": mu, "ref_std": sigma},
            )
        s_hi = 0.0
        s_lo = 0.0
        for x in values:
            z = (x - mu) / sigma
            s_hi = max(0.0, s_hi + z - k)
            s_lo = min(0.0, s_lo + z + k)
        raw = max(s_hi, -s_lo)
        score = raw / h
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"CUSUM alarm level = {score:.3f} "
                f"({'alarm' if score >= 1.0 else 'normal'}; "
                f"S_hi={s_hi:.2f}, S_lo={s_lo:.2f})"
            ),
            details={"cusum_hi": s_hi, "cusum_lo": s_lo, "ref_mean": mu, "ref_std": sigma},
        )

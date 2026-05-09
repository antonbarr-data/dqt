# Standard Z-score outlier detection. Use only after verifying normality.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class ZScoreDetector(BaseDetector):
    """Z-score outlier detection. Score = fraction with |Z| > threshold. Assumes normality."""
    slug = "zscore_outlier_fraction"
    group = "outliers_uni"

    def __init__(self, threshold: float = 3.0) -> None:
        self._threshold = threshold

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        std = float(np.std(col, ddof=1))
        return {"mean": float(np.mean(col)), "std": std if std > 0 else 1.0}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        z = np.abs((col - state["mean"]) / state["std"])
        outlier_frac = float(np.mean(z > self._threshold))
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of values have |Z| > {self._threshold} (μ={state['mean']:.3g}, σ={state['std']:.3g})",
            details={"outlier_fraction": outlier_frac, "threshold": self._threshold,
                     "mean": state["mean"], "std": state["std"]},
        )

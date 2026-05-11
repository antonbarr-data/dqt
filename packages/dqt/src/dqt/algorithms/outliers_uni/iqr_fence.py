# packages/dqt/src/dqt/algorithms/outliers_uni/iqr_fence.py
# Ref: Tukey (1977) Exploratory Data Analysis — inner fences Q1−k·IQR, Q3+k·IQR
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class IQRFenceDetector(BaseDetector):
    """Tukey IQR fence outlier detection. Score = fraction of values outside [Q1−k·IQR, Q3+k·IQR]."""
    slug = "iqr_fence"
    group = "outliers_uni"

    def __init__(self, k: float = 3.0) -> None:
        self._k = k

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        q1, q3 = float(np.percentile(col, 25)), float(np.percentile(col, 75))
        iqr = q3 - q1
        return {"lower": q1 - self._k * iqr, "upper": q3 + self._k * iqr}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        n = len(col)
        n_out = int(np.sum((col < state["lower"]) | (col > state["upper"])))
        frac = n_out / n if n > 0 else 0.0
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{frac:.1%} of values outside Tukey fences "
                f"[{state['lower']:.3g}, {state['upper']:.3g}]"
            ),
            details={
                "outlier_fraction": frac,
                "lower_fence": state["lower"],
                "upper_fence": state["upper"],
            },
        )

# Ref: Hubert & Vandervieren (2008) CSDA — An adjusted boxplot for skewed distributions.
# Medcouple-corrected Tukey fences: for MC >= 0 (right skew):
#   lower = Q1 − h·exp(−4·MC)·IQR,  upper = Q3 + h·exp(3·MC)·IQR
# For MC < 0 (left skew): lower uses exp(−3·MC), upper uses exp(4·MC).
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


def _adjusted_fences(values: np.ndarray, h: float = 1.5) -> tuple[float, float]:
    from dqt.algorithms.distribution.profiler import _medcouple
    q1, q3 = float(np.percentile(values, 25)), float(np.percentile(values, 75))
    iqr = q3 - q1
    mc = _medcouple(values)
    if mc >= 0:
        lower = q1 - h * np.exp(-4.0 * mc) * iqr
        upper = q3 + h * np.exp(3.0 * mc) * iqr
    else:
        lower = q1 - h * np.exp(-3.0 * mc) * iqr
        upper = q3 + h * np.exp(4.0 * mc) * iqr
    return float(lower), float(upper)


@registry.register
class AdjustedBoxplotDetector(BaseDetector):
    """Medcouple-adjusted boxplot outlier detection for skewed distributions."""
    slug = "adjusted_boxplot_fraction"
    group = "outliers_uni"

    def __init__(self, h: float = 1.5) -> None:
        self._h = h

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        lower, upper = _adjusted_fences(col, self._h)
        return {"lower": lower, "upper": upper, "h": self._h}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        n = len(col)
        n_out = int(np.sum((col < state["lower"]) | (col > state["upper"])))
        outlier_frac = n_out / n if n > 0 else 0.0
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=(
                f"{outlier_frac:.1%} of values outside medcouple-adjusted fences "
                f"[{state['lower']:.3g}, {state['upper']:.3g}]"
            ),
            details={
                "outlier_fraction": outlier_frac,
                "lower_fence": state["lower"],
                "upper_fence": state["upper"],
            },
        )

# Ref (MAD): Leys et al. (2013) J. Exp. Soc. Psychol. — modified Z-score with MAD, threshold 3.5
# Ref (Double MAD): Rousseeuw & Croux (1993) JASA — asymmetric MAD for skewed distributions
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry

_MAD_CONSISTENCY = 0.6745  # makes MAD a consistent estimator of σ under normality


@registry.register
class MADOutlierDetector(BaseDetector):
    """Modified Z-score outlier detection. Score = fraction of values with |mod-Z| > threshold."""
    slug = "mad_outlier_fraction"
    group = "outliers_uni"

    def __init__(self, threshold: float = 3.5) -> None:
        self._threshold = threshold

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        median = float(np.median(col))
        mad = float(np.median(np.abs(col - median)))
        return {"median": median, "mad": mad if mad > 0 else 1.0}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        mod_z = _MAD_CONSISTENCY * np.abs(col - state["median"]) / state["mad"]
        outlier_frac = float(np.mean(mod_z > self._threshold))
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of values are outliers (modified Z > {self._threshold})",
            details={"outlier_fraction": outlier_frac, "threshold": self._threshold},
        )


@registry.register
class DoubleMadOutlierDetector(BaseDetector):
    """
    Asymmetric double-MAD outlier detection for skewed distributions.
    Computes separate MAD_left and MAD_right from the median, so a heavy right tail
    does not inflate the left-side threshold (and vice versa).
    """
    slug = "double_mad_outlier_fraction"
    group = "outliers_uni"

    def __init__(self, threshold: float = 3.5) -> None:
        self._threshold = threshold

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        median = float(np.median(col))
        deviations = np.abs(col - median)
        mad_left = float(np.median(deviations[col <= median])) if np.any(col <= median) else 1.0
        mad_right = float(np.median(deviations[col >= median])) if np.any(col >= median) else 1.0
        return {
            "median": median,
            "mad_left": mad_left if mad_left > 0 else 1.0,
            "mad_right": mad_right if mad_right > 0 else 1.0,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        median: float = state["median"]
        side_mad = np.where(col < median, state["mad_left"], state["mad_right"])
        mod_z = _MAD_CONSISTENCY * np.abs(col - median) / side_mad
        outlier_frac = float(np.mean(mod_z > self._threshold))
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of values are outliers (double-MAD modified Z > {self._threshold})",
            details={
                "outlier_fraction": outlier_frac,
                "threshold": self._threshold,
                "mad_left": state["mad_left"],
                "mad_right": state["mad_right"],
            },
        )

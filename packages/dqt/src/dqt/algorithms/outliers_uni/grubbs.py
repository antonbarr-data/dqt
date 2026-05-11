# packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py
# Ref: Grubbs (1950) Ann. Math. Statist. — outlier test using max |xi-x̄|/s
# Ref: Rosner (1983) Technometrics — generalized ESD for up to k outliers
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from typing import ClassVar

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


def _grubbs_p_value(values: np.ndarray) -> float:
    """Return p-value for the Grubbs test (two-tailed)."""
    n = len(values)
    if n < 3:
        return 1.0
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    if std == 0.0:
        return 1.0
    G = float(np.max(np.abs(values - mean)) / std)
    denom = (n - 1) ** 2 - G ** 2 * n
    if denom <= 0:
        return 0.0
    t_stat = float(np.sqrt(G ** 2 * n * (n - 2) / denom))
    p_one = float(1.0 - stats.t.cdf(t_stat, df=n - 2))
    return float(min(2.0 * n * p_one, 1.0))


@registry.register
class GrubbsDetector(BaseDetector):
    """Grubbs' test for a single outlier. Score = 1 − p-value; warn p<0.05, fail p<0.01."""
    slug = "grubbs"
    group = "outliers_uni"
    min_recommended_n: ClassVar[int] = 25

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(col) < 3:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient data for Grubbs test.",
                details={"p_value": 1.0},
            )
        p_value = _grubbs_p_value(col)
        score = float(1.0 - p_value)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Grubbs test p={p_value:.4f} — "
                f"{'outlier detected' if score > 0.95 else 'no outlier detected'}"
            ),
            details={"p_value": p_value},
        )


def _gesd_n_outliers(values: np.ndarray, max_outliers: int, alpha: float = 0.05) -> int:
    """Rosner's Generalized ESD. Returns the number of outliers found."""
    n = len(values)
    work = values.copy().astype(float)
    n_found = 0
    for i in range(1, max_outliers + 1):
        if len(work) < 3:
            break
        mean = float(np.mean(work))
        std = float(np.std(work, ddof=1))
        if std == 0.0:
            break
        idx = int(np.argmax(np.abs(work - mean)))
        R = float(abs(work[idx] - mean) / std)
        m = len(work)
        p = alpha / (2.0 * (n - i + 1))
        t_crit = float(stats.t.ppf(1.0 - p, df=m - 2))
        lam = float((m - 1) * t_crit / np.sqrt(m * ((m - 2) + t_crit ** 2)))
        if R > lam:
            n_found = i
        work = np.delete(work, idx)
    return n_found


@registry.register
class GeneralizedESDDetector(BaseDetector):
    """Rosner Generalized ESD test for up to max_outliers outliers. Score = outlier fraction."""
    slug = "generalized_esd"
    group = "outliers_uni"
    min_recommended_n: ClassVar[int] = 50

    def __init__(self, max_outliers: int = 0, alpha: float = 0.05) -> None:
        self._max_outliers = max_outliers  # 0 = auto: max(10, 10% of n)
        self._alpha = alpha

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        n = len(col)
        if n < 6:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient data for GESD test (need >= 6 values).",
                details={"n_outliers": 0, "n": n},
            )
        # Cap at 100: GESD is O(n*k) and designed for small datasets.
        # For large n the fraction threshold (1%) governs; absolute count > 100 is irrelevant.
        max_k = self._max_outliers if self._max_outliers > 0 else min(max(10, n // 10), 100)
        n_out = _gesd_n_outliers(col, max_outliers=max_k, alpha=self._alpha)
        frac = n_out / n
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"GESD found {n_out} outlier{'s' if n_out != 1 else ''} ({frac:.1%} of {n} values)",
            details={"n_outliers": n_out, "n": n, "max_k_tested": max_k},
        )

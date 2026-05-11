# packages/dqt/src/dqt/algorithms/pattern/benford.py
# Ref: Benford (1938) Proc. Am. Philos. Soc. — first-digit law: P(d) = log10(1 + 1/d)
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

# Benford's expected first-digit probabilities for digits 1..9
_BENFORD_EXPECTED = np.array(
    [np.log10(1.0 + 1.0 / d) for d in range(1, 10)], dtype=float
)


def _first_digits(col: np.ndarray) -> np.ndarray:
    """Extract first significant digit (1–9) from each value."""
    abs_vals = np.abs(col[col != 0])
    if len(abs_vals) == 0:
        return np.array([], dtype=int)
    magnitudes = np.floor(np.log10(abs_vals))
    normalized = abs_vals / (10.0 ** magnitudes)
    return np.floor(normalized).astype(int)


@registry.register
class BenfordDetector(BaseDetector):
    """Benford's Law fit test. Score = 1 − p-value from chi-square vs expected first-digit frequencies."""
    slug = "benford_law_fit"
    group = "pattern"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        digits = _first_digits(col)
        if len(digits) < 30:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient data for Benford's Law test (need >= 30 non-zero values).",
                details={"p_value": 1.0, "chi2_statistic": 0.0, "digit_fractions": []},
            )
        observed = np.array([np.sum(digits == d) for d in range(1, 10)], dtype=float)
        expected = _BENFORD_EXPECTED * len(digits)
        chi2, p_value = stats.chisquare(observed, f_exp=expected)
        score = float(1.0 - p_value)
        digit_fracs = (observed / observed.sum()).tolist()
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Benford's Law chi-square p={p_value:.4f} — "
                f"{'deviation detected' if score > 0.95 else 'conforms to Benford'}"
            ),
            details={
                "p_value": float(p_value),
                "chi2_statistic": float(chi2),
                "digit_fractions": digit_fracs,
            },
        )

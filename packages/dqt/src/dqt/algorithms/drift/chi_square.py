# packages/dqt/src/dqt/algorithms/drift/chi_square.py
# Ref: Pearson (1900) Philosophical Magazine — chi-square goodness-of-fit test for categorical drift
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class ChiSquareDriftDetector(BaseDetector):
    """Chi-square test for categorical distribution drift. Score = 1 − p-value."""
    slug = "chi_square_drift"
    group = "drift"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().astype(str)
        counts = col.value_counts()
        total = len(col)
        expected_frac = {cat: cnt / total for cat, cnt in counts.items()}
        return {"expected_frac": expected_frac, "categories": list(counts.index)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().astype(str)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"p_value": 1.0},
            )
        n = len(curr)
        categories = state["categories"]
        curr_counts = curr.value_counts()
        observed = np.array([curr_counts.get(cat, 0) for cat in categories], dtype=float)
        expected = np.array([state["expected_frac"][cat] * n for cat in categories], dtype=float)
        # Drop zero-expected bins to avoid division by zero
        mask = expected > 0
        observed, expected = observed[mask], expected[mask]
        if len(observed) < 2:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient categories for chi-square test.",
                details={"p_value": 1.0},
            )
        _, p_value = stats.chisquare(observed, f_exp=expected)
        score = float(1.0 - p_value)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Chi-square test p={p_value:.4f} — "
                f"{'categorical drift detected' if score > 0.95 else 'stable'}"
            ),
            details={
                "p_value": float(p_value),
                "chi2_statistic": float(np.sum((observed - expected) ** 2 / expected)),
            },
        )

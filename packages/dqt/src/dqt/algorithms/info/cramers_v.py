# packages/dqt/src/dqt/algorithms/info/cramers_v.py
# Ref: Cramér (1946) Mathematical Methods of Statistics
# V = sqrt(χ² / (n · min(r−1, c−1))); for drift: 2-period × K-category contingency table
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class CramersVDetector(BaseDetector):
    """Cramér's V categorical drift. Builds 2×K contingency (reference vs current). Score = V."""
    slug = "cramers_v"
    group = "info"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().astype(str)
        counts = col.value_counts()
        return {"ref_counts": counts.to_dict(), "categories": list(counts.index)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().astype(str)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"cramers_v": 0.0},
            )
        categories = state["categories"]
        curr_counts = curr.value_counts().to_dict()
        row_ref = np.array([state["ref_counts"].get(c, 0) for c in categories], dtype=float)
        row_cur = np.array([curr_counts.get(c, 0) for c in categories], dtype=float)
        contingency = np.vstack([row_ref, row_cur])
        chi2, _, _, _ = stats.chi2_contingency(contingency, correction=False)
        n = contingency.sum()
        k = len(categories)
        if n == 0 or k < 2:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient data for Cramér's V.",
                details={"cramers_v": 0.0},
            )
        v = float(np.sqrt(chi2 / (n * (min(2, k) - 1))))
        v = min(max(v, 0.0), 1.0)
        return DetectorResult(
            score=v,
            verdict=self._verdict(v),
            plain_english=f"Cramér's V = {v:.4f} — {'categorical drift' if v >= 0.15 else 'stable'}",
            details={"cramers_v": v, "chi2": float(chi2), "n": float(n)},
        )

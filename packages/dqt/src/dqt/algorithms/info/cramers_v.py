# packages/dqt/src/dqt/algorithms/info/cramers_v.py
# Ref: Cramér (1946) Mathematical Methods of Statistics; Bergsma & Wicher (2013) J. Stat. Planning
# V = sqrt(χ² / (n · min(r−1, c−1))); bias-corrected per Bergsma-Wicher (2013)
from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


def _cramers_v_corrected(chi2: float, n: float, k: int, r: int = 2) -> float:
    """Bergsma-Wicher bias-corrected Cramér's V. Corrects positive bias in small samples."""
    if n <= 1:
        return 0.0
    phi2 = chi2 / n
    phi2_corr = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    k_corr = k - (k - 1) ** 2 / (n - 1)
    r_corr = r - (r - 1) ** 2 / (n - 1)
    denom = min(k_corr, r_corr) - 1
    if denom <= 0:
        return 0.0
    return float(np.sqrt(max(0.0, phi2_corr / denom)))


@registry.register
class CramersVDetector(BaseDetector):
    """Cramér's V categorical drift. Builds 2×K contingency (reference vs current). Score = V."""
    slug = "cramers_v"
    group = "info"
    version: ClassVar[str] = "2"

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
                details={"cramers_v": 0.0, "bias_corrected": True},
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
                details={"cramers_v": 0.0, "bias_corrected": True},
            )
        v = _cramers_v_corrected(chi2, n, k, r=2)
        v = min(max(v, 0.0), 1.0)
        return DetectorResult(
            score=v,
            verdict=self._verdict(v),
            plain_english=f"Cramér's V = {v:.4f} — {'categorical drift' if v >= 0.15 else 'stable'}",
            details={"cramers_v": v, "chi2": float(chi2), "n": float(n), "bias_corrected": True},
        )

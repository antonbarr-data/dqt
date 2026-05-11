# Ref: Kolmogorov (1933), Smirnov (1948) — two-sample KS test via scipy.stats.ks_2samp
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from typing import ClassVar

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class KS2SampleDetector(BaseDetector):
    """Two-sample KS test for distribution drift. Score = 1 − p-value; warn p<0.05, fail p<0.01."""
    slug = "ks_pvalue"
    group = "drift"
    min_recommended_n: ClassVar[int] = 500

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {"reference": reference.iloc[:, 0].dropna().to_numpy(dtype=float)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0 or len(state["reference"]) == 0:
            return DetectorResult(
                score=0.0,
                verdict=Verdict.pass_,
                plain_english="Insufficient data for KS test.",
                details={"p_value": 1.0, "ks_statistic": 0.0},
            )
        ks_stat, p_value = stats.ks_2samp(state["reference"], curr)
        score = 1.0 - float(p_value)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"KS test p={p_value:.4f} — "
                f"{'drift detected' if score > 0.95 else 'no significant drift'}"
            ),
            details={"ks_statistic": float(ks_stat), "p_value": float(p_value)},
        )

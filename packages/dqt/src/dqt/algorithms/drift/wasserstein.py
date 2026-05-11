# packages/dqt/src/dqt/algorithms/drift/wasserstein.py
# Ref: Kantorovich (1942); Wasserstein (1969) — 1-Wasserstein (earth-mover) distance
# Score = wasserstein_distance(ref, curr) / std(ref); dimensionless shift in units of σ
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from typing import ClassVar

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


@registry.register
class Wasserstein1Detector(BaseDetector):
    """Wasserstein-1 (earth-mover) distance for distribution drift. Score normalised by reference std."""
    slug = "wasserstein_1"
    group = "drift"
    min_recommended_n: ClassVar[int] = 500

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        return {"reference": col, "ref_std": max(float(np.std(col, ddof=1)), _EPSILON)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"raw_distance": 0.0, "ref_std": state["ref_std"]},
            )
        raw = float(stats.wasserstein_distance(state["reference"], curr))
        score = raw / state["ref_std"]
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Wasserstein-1 distance = {raw:.4g} "
                f"({score:.2f}σ of reference); "
                f"{'drift detected' if score >= 0.20 else 'stable'}"
            ),
            details={"raw_distance": raw, "ref_std": state["ref_std"]},
        )

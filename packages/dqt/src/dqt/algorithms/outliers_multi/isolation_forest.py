# Ref: Liu et al. (2008) ICDM — Isolation Forest; sklearn implementation
# score_samples() returns raw anomaly scores; threshold derived from reference percentile so
# the detector measures "how anomalous vs baseline" rather than always returning contamination%.
from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class IsolationForestDetector(BaseDetector):
    """Isolation Forest multivariate outlier detection. Score = fraction of rows flagged anomalous."""
    slug = "isolation_forest_fraction"
    group = "outliers_multi"
    min_recommended_n: ClassVar[int] = 200

    def __init__(self, contamination: float = 0.05) -> None:
        self._contamination = contamination

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from sklearn.ensemble import IsolationForest
        X = reference.select_dtypes(include="number").fillna(0.0)
        # contamination='auto' avoids baking the expected-fraction into the model's
        # internal threshold — we derive our own threshold from score_samples().
        model = IsolationForest(contamination="auto", random_state=42, n_estimators=100)
        model.fit(X)
        ref_scores = model.score_samples(X)
        # Threshold = contamination-percentile of reference scores.
        # Values below this on NEW data are flagged; clean data returns ≈contamination%,
        # anomalous data returns significantly more.
        threshold = float(np.percentile(ref_scores, self._contamination * 100))
        return {
            "model": model,
            "columns": list(X.columns),
            "threshold": threshold,
            "contamination": self._contamination,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        model = state["model"]
        cols: list[str] = state["columns"]
        missing = [c for c in cols if c not in current.columns]
        if missing:
            raise ValueError(f"IsolationForest: columns missing in current data: {missing}")
        X = current[cols].fillna(0.0)
        raw_scores = model.score_samples(X)
        outlier_frac = float(np.mean(raw_scores < state["threshold"]))
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of rows flagged as multivariate outliers by Isolation Forest",
            details={
                "outlier_fraction": outlier_frac,
                "n_rows": len(X),
                "n_features": len(cols),
                "threshold": state["threshold"],
            },
        )

# Ref: Liu et al. (2008) ICDM — Isolation Forest; sklearn implementation
# score_samples() gives raw anomaly scores (lower = more anomalous). We store the 5th
# percentile of reference scores as a fixed threshold so current-data outlier fraction
# is measured against the reference distribution, not re-calibrated per batch.
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

    def __init__(self, reference_pct: float = 5.0) -> None:
        """
        reference_pct: percentile of reference anomaly scores used as the fixed decision
        threshold. Default 5.0 means ~5% of in-distribution data falls below the threshold.
        """
        self._reference_pct = reference_pct

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from sklearn.ensemble import IsolationForest
        X = reference.select_dtypes(include="number").fillna(0.0)
        if X.shape[1] < 2:
            raise ValueError(
                "IsolationForest requires ≥2 numeric columns. "
                "For single-column outlier detection use 'ecod' or 'lof' instead."
            )
        model = IsolationForest(contamination="auto", random_state=42, n_estimators=100)
        model.fit(X)
        ref_scores = model.score_samples(X)
        # Fixed threshold: points below this percentile of reference scores are outliers.
        threshold = float(np.percentile(ref_scores, self._reference_pct))
        return {
            "model": model,
            "columns": list(X.columns),
            "score_threshold": threshold,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        model = state["model"]
        cols: list[str] = state["columns"]
        missing = [c for c in cols if c not in current.columns]
        if missing:
            raise ValueError(f"IsolationForest: columns missing in current data: {missing}")
        X = current[cols].fillna(0.0)
        curr_scores = model.score_samples(X)
        outlier_frac = float(np.mean(curr_scores < state["score_threshold"]))
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of rows flagged as multivariate outliers by Isolation Forest",
            details={
                "outlier_fraction": outlier_frac,
                "n_rows": len(X),
                "n_features": len(cols),
                "score_threshold": state["score_threshold"],
            },
        )

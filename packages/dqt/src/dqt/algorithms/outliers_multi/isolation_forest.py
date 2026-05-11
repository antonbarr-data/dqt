# Ref: Liu et al. (2008) ICDM — Isolation Forest; sklearn implementation
# Uses predict() so sklearn's internally calibrated threshold (set at fit time so that
# contamination% of training points are labeled outliers) is used — dirty test data
# returns a strictly higher outlier fraction than clean data from the same distribution.
from __future__ import annotations

from typing import ClassVar

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
        model = IsolationForest(contamination=self._contamination, random_state=42, n_estimators=100)
        model.fit(X)
        return {
            "model": model,
            "columns": list(X.columns),
            "contamination": self._contamination,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        model = state["model"]
        cols: list[str] = state["columns"]
        missing = [c for c in cols if c not in current.columns]
        if missing:
            raise ValueError(f"IsolationForest: columns missing in current data: {missing}")
        X = current[cols].fillna(0.0)
        predictions = model.predict(X)
        outlier_frac = float((predictions == -1).mean())
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of rows flagged as multivariate outliers by Isolation Forest",
            details={
                "outlier_fraction": outlier_frac,
                "n_rows": len(X),
                "n_features": len(cols),
            },
        )

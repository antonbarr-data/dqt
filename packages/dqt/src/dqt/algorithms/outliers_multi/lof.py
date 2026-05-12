# packages/dqt/src/dqt/algorithms/outliers_multi/lof.py
# Ref: Breunig et al. (2000) ACM SIGMOD — LOF: Identifying Density-Based Local Outliers
# Score = fraction of rows with LOF > reference 95th percentile LOF score.
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class LOFDetector(BaseDetector):
    """Local Outlier Factor multivariate outlier detector. Score = fraction of rows with LOF above reference 95th pct."""
    slug = "lof"
    group = "outliers_multi"

    def __init__(self, n_neighbors: int | None = None) -> None:
        self._n_neighbors = n_neighbors

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        columns = list(reference.select_dtypes(include="number").columns)
        n = len(X)
        k = self._n_neighbors if self._n_neighbors is not None else max(5, math.ceil(math.sqrt(n)))
        k = min(k, max(1, n - 1))
        clf = LocalOutlierFactor(n_neighbors=k, novelty=True)
        clf.fit(X)
        ref_scores = -clf.score_samples(X)
        threshold = float(np.percentile(ref_scores, 99))
        return {"model": clf, "columns": columns, "threshold": threshold, "k": k}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "lof_threshold": state["threshold"], "n_rows": 0, "k": state["k"]},
            )
        lof_scores = -state["model"].score_samples(X)
        n_out = int(np.sum(lof_scores > state["threshold"]))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows with LOF score above reference 95th percentile",
            details={"outlier_fraction": frac, "lof_threshold": state["threshold"], "n_rows": len(X), "k": state["k"]},
        )

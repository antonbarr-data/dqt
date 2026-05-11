# packages/dqt/src/dqt/algorithms/outliers_multi/one_class_svm.py
# Ref: Schölkopf et al. (2001) Neural Computation — Estimating support of a high-dimensional distribution
# Score = fraction of rows predicted as outliers (-1) by the fitted OC-SVM.
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.svm import OneClassSVM

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class OneClassSVMDetector(BaseDetector):
    """One-Class SVM multivariate outlier detector. Score = fraction of rows classified as outliers."""
    slug = "one_class_svm"
    group = "outliers_multi"

    def __init__(self, nu: float = 0.01, kernel: str = "rbf") -> None:
        self._nu = nu
        self._kernel = kernel

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        model = OneClassSVM(nu=self._nu, kernel=self._kernel)
        model.fit(X)
        return {
            "model": model,
            "columns": list(reference.select_dtypes(include="number").columns),
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols: list[str] = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "n_rows": 0},
            )
        preds = state["model"].predict(X)  # -1 = outlier, 1 = inlier
        n_out = int(np.sum(preds == -1))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows classified as outliers by One-Class SVM",
            details={"outlier_fraction": frac, "n_rows": len(X)},
        )

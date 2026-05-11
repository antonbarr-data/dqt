# packages/dqt/src/dqt/algorithms/outliers_multi/ecod.py
# Ref: Li et al. (2022) IEEE TKDE — ECOD: Unsupervised Outlier Detection Using Empirical CDF Functions
# Score(x) = -log(min(ECDF(xi), 1-ECDF(xi))) summed; fraction above reference 99th pct.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-6


def _ecdf(ref: np.ndarray, x: np.ndarray) -> np.ndarray:
    n = len(ref)
    ref_sorted = np.sort(ref)
    return np.searchsorted(ref_sorted, x, side="right") / n


def _ecod_scores(X: np.ndarray, ref: np.ndarray) -> np.ndarray:
    n_rows, n_cols = X.shape
    scores = np.zeros(n_rows)
    for j in range(n_cols):
        ecdf_vals = _ecdf(ref[:, j], X[:, j])
        ecdf_vals = np.clip(ecdf_vals, _EPSILON, 1.0 - _EPSILON)
        tail_prob = np.minimum(ecdf_vals, 1.0 - ecdf_vals)
        scores += -np.log(tail_prob)
    return scores


@registry.register
class ECODDetector(BaseDetector):
    """ECOD — Empirical CDF outlier detection. Score = fraction above reference 99th percentile."""
    slug = "ecod"
    group = "outliers_multi"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        columns = list(reference.select_dtypes(include="number").columns)
        ref_scores = _ecod_scores(X, X)
        threshold = float(np.percentile(ref_scores, 99))
        return {"reference": X, "columns": columns, "threshold": threshold}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "score_threshold": state["threshold"]},
            )
        scores = _ecod_scores(X, state["reference"])
        n_out = int(np.sum(scores > state["threshold"]))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows with ECOD score above reference 99th percentile",
            details={"outlier_fraction": frac, "score_threshold": state["threshold"]},
        )

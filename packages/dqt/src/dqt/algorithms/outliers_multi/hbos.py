# packages/dqt/src/dqt/algorithms/outliers_multi/hbos.py
# Ref: Goldstein & Dengel (2012) KI-2012 — Histogram-based Outlier Score
# HBOS(x) = Σ_i log(1 / freq(xi in bin_i)); score = fraction above reference 95th percentile.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-6


def _hbos_scores(X: np.ndarray, bin_edges_list: list, n_bins: int) -> np.ndarray:
    scores = np.zeros(len(X))
    for j, edges in enumerate(bin_edges_list):
        col = X[:, j]
        counts, _ = np.histogram(col, bins=edges)
        freqs = (counts + _EPSILON) / (len(col) + n_bins * _EPSILON)
        indices = np.clip(np.digitize(col, edges[1:-1]), 0, n_bins - 1)
        scores += np.log(1.0 / freqs[indices])
    return scores


@registry.register
class HBOSDetector(BaseDetector):
    """Histogram-Based Outlier Score. Score = fraction of rows above reference 99th percentile HBOS."""
    slug = "hbos"
    group = "outliers_multi"

    def __init__(self, n_bins: int = 20) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        columns = list(reference.select_dtypes(include="number").columns)
        bin_edges_list = [
            np.histogram_bin_edges(X[:, j], bins=self._n_bins)
            for j in range(X.shape[1])
        ]
        ref_scores = _hbos_scores(X, bin_edges_list, self._n_bins)
        threshold = float(np.percentile(ref_scores, 99))
        return {
            "bin_edges_list": bin_edges_list,
            "columns": columns,
            "threshold": threshold,
            "n_bins": self._n_bins,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "score_threshold": state["threshold"]},
            )
        scores = _hbos_scores(X, state["bin_edges_list"], state["n_bins"])
        n_out = int(np.sum(scores > state["threshold"]))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows with HBOS score above reference 99th percentile",
            details={"outlier_fraction": frac, "score_threshold": state["threshold"]},
        )

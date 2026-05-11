# packages/dqt/src/dqt/algorithms/drift/divergence.py
# Ref: Kullback & Leibler (1951) Ann. Math. Statist. — KL divergence
# Ref: Lin (1991) IEEE Trans. Inf. Theory — Jensen-Shannon divergence
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


def _histogram_probs(col: np.ndarray, bin_edges: np.ndarray) -> np.ndarray:
    counts, _ = np.histogram(col, bins=bin_edges)
    probs = counts + _EPSILON
    return probs / probs.sum()


@registry.register
class KLDivergenceDetector(BaseDetector):
    """KL divergence drift detector (binned). Score = KL(current ‖ reference)."""
    slug = "kl_divergence"
    group = "drift"

    def __init__(self, n_bins: int = 10) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        bin_edges = np.histogram_bin_edges(col, bins=self._n_bins)
        ref_probs = _histogram_probs(col, bin_edges)
        return {"bin_edges": bin_edges, "ref_probs": ref_probs}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"kl_divergence": 0.0},
            )
        cur_probs = _histogram_probs(curr, state["bin_edges"])
        kl = float(np.sum(cur_probs * np.log(cur_probs / state["ref_probs"])))
        kl = max(0.0, kl)
        return DetectorResult(
            score=kl,
            verdict=self._verdict(kl),
            plain_english=f"KL divergence = {kl:.4f} — {'drift detected' if kl >= 0.10 else 'stable'}",
            details={"kl_divergence": kl},
        )


@registry.register
class JSDivergenceDetector(BaseDetector):
    """Jensen-Shannon distance drift detector (binned, bounded [0,1])."""
    slug = "js_divergence"
    group = "drift"

    def __init__(self, n_bins: int = 10) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        bin_edges = np.histogram_bin_edges(col, bins=self._n_bins)
        ref_probs = _histogram_probs(col, bin_edges)
        return {"bin_edges": bin_edges, "ref_probs": ref_probs}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"js_distance": 0.0},
            )
        cur_probs = _histogram_probs(curr, state["bin_edges"])
        js = float(jensenshannon(state["ref_probs"], cur_probs))
        js = min(max(js, 0.0), 1.0)
        return DetectorResult(
            score=js,
            verdict=self._verdict(js),
            plain_english=f"JS distance = {js:.4f} — {'drift detected' if js >= 0.10 else 'stable'}",
            details={"js_distance": js},
        )

# packages/dqt/src/dqt/algorithms/info/mutual_information.py
# Ref: Cover & Thomas (2006) Elements of Information Theory
# NMI = MI / sqrt(H(X) * H(Y)); bounded [0, 1]; higher = more shared info = less drift.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-10


def _entropy(probs: np.ndarray) -> float:
    p = probs[probs > 0]
    return float(-np.sum(p * np.log(p)))


def _normalized_mi(ref: np.ndarray, curr: np.ndarray, bin_edges: np.ndarray) -> float:
    """Normalized mutual information via a joint histogram over shared bin edges."""
    ref_idx = np.digitize(ref, bin_edges[1:-1])
    cur_idx = np.digitize(curr, bin_edges[1:-1])
    n_bins = len(bin_edges) - 1

    joint = np.zeros((n_bins, n_bins), dtype=float)
    for r, c in zip(ref_idx, cur_idx):
        ri = min(r, n_bins - 1)
        ci = min(c, n_bins - 1)
        joint[ri, ci] += 1.0

    joint += _EPSILON
    joint /= joint.sum()
    p_ref = joint.sum(axis=1)
    p_cur = joint.sum(axis=0)

    H_ref = _entropy(p_ref)
    H_cur = _entropy(p_cur)
    denom = np.sqrt(H_ref * H_cur)
    if denom < _EPSILON:
        return 1.0

    H_joint = _entropy(joint.ravel())
    mi = H_ref + H_cur - H_joint
    return float(min(max(mi / denom, 0.0), 1.0))


@registry.register
class MutualInformationDetector(BaseDetector):
    """Normalized Mutual Information for drift detection. Score = NMI (higher = more similar)."""
    slug = "mutual_information"
    group = "info"

    def __init__(self, n_bins: int = 20) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        ref = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        bin_edges = np.histogram_bin_edges(ref, bins=self._n_bins)
        return {"reference": ref, "bin_edges": bin_edges, "n_bins": self._n_bins}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=1.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"normalized_mi": 1.0, "n_bins": state["n_bins"]},
            )
        nmi = _normalized_mi(state["reference"], curr, state["bin_edges"])
        return DetectorResult(
            score=nmi,
            verdict=self._verdict(nmi),
            plain_english=(
                f"Normalized MI = {nmi:.4f} — "
                f"{'stable' if nmi >= 0.50 else 'drift detected'}"
            ),
            details={"normalized_mi": nmi, "n_bins": state["n_bins"]},
        )

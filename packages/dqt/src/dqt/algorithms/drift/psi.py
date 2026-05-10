# packages/dqt/src/dqt/algorithms/drift/psi.py
# Ref: PSI (Population Stability Index) — credit risk industry standard
# PSI = Σ (actual_% − expected_%) × ln(actual_% / expected_%)
# Thresholds: <0.1 stable, 0.1–0.2 moderate shift, >0.2 significant shift
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-6


@registry.register
class PSIDetector(BaseDetector):
    """Population Stability Index drift detector. Score = PSI value."""
    slug = "psi"
    group = "drift"

    def __init__(self, n_bins: int = 10) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        bin_edges = np.histogram_bin_edges(col, bins=self._n_bins)
        ref_counts, _ = np.histogram(col, bins=bin_edges)
        ref_frac = (ref_counts + _EPSILON) / (len(col) + self._n_bins * _EPSILON)
        return {"bin_edges": bin_edges, "ref_frac": ref_frac, "n_bins": self._n_bins}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"psi": 0.0, "n_bins": state["n_bins"]},
            )
        cur_counts, _ = np.histogram(curr, bins=state["bin_edges"])
        cur_frac = (cur_counts + _EPSILON) / (len(curr) + state["n_bins"] * _EPSILON)
        psi = float(np.sum((cur_frac - state["ref_frac"]) * np.log(cur_frac / state["ref_frac"])))
        psi = max(0.0, psi)
        verdict_label = (
            "significant population shift" if psi > 0.20
            else "moderate shift" if psi > 0.10
            else "stable"
        )
        return DetectorResult(
            score=psi,
            verdict=self._verdict(psi),
            plain_english=f"PSI = {psi:.4f} — {verdict_label}",
            details={"psi": psi, "n_bins": state["n_bins"]},
        )

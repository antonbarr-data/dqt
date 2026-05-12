# packages/dqt/src/dqt/algorithms/outliers_multi/mahalanobis.py
# Ref: Mahalanobis (1936) Proc. Natl. Inst. Sci. India
# Score = fraction of rows with d² > chi2(p, df=n_features) critical value at p=0.01.
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-10


@registry.register
class MahalanobisDetector(BaseDetector):
    """Mahalanobis distance multivariate outlier detector. Score = fraction outside chi-square ellipsoid."""
    slug = "mahalanobis_distance"
    group = "outliers_multi"

    def __init__(self, p_threshold: float = 0.001) -> None:
        self._p_threshold = p_threshold

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        columns = list(reference.select_dtypes(include="number").columns)
        mean = np.mean(X, axis=0)
        cov = np.cov(X, rowvar=False)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])
        rank = np.linalg.matrix_rank(cov)
        singular = bool(rank < cov.shape[0])
        if singular:
            cov_inv = np.linalg.pinv(cov)
        else:
            try:
                cov_inv = np.linalg.inv(cov + _EPSILON * np.eye(cov.shape[0]))
            except np.linalg.LinAlgError:
                cov_inv = np.linalg.pinv(cov)
                singular = True
        df = X.shape[1]
        chi2_threshold = float(scipy_stats.chi2.ppf(1.0 - self._p_threshold, df=df))
        return {
            "mean": mean,
            "cov_inv": cov_inv,
            "columns": columns,
            "chi2_threshold": chi2_threshold,
            "n_features": df,
            "singular_cov": singular,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "chi2_threshold": state["chi2_threshold"], "n_rows": 0},
            )
        diff = X - state["mean"]
        d_sq = np.einsum("ij,jk,ik->i", diff, state["cov_inv"], diff)
        n_out = int(np.sum(d_sq > state["chi2_threshold"]))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows outside Mahalanobis chi-square ellipsoid (p={self._p_threshold})",
            details={
                "outlier_fraction": frac,
                "chi2_threshold": state["chi2_threshold"],
                "n_rows": len(X),
                "singular_covariance": state.get("singular_cov", False),
            },
        )

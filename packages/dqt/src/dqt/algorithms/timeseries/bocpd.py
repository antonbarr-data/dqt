# packages/dqt/src/dqt/algorithms/timeseries/bocpd.py
# Ref: Adams & MacKay (2007) arXiv:0710.3742 — Bayesian Online Changepoint Detection
# Gaussian likelihood, student-t predictive (normal-inverse-chi-sq conjugate), hazard=1/lambda.
# Truncated run-length posterior to prevent collapse to a single dominant hypothesis.
# Pure numpy + scipy — no ruptures or other external deps.
from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-12


def _bocpd_run(
    data: np.ndarray,
    mu0: float,
    kappa0: float,
    alpha0: float,
    beta0: float,
    hazard_lambda: float,
    max_run: int,
) -> np.ndarray:
    """Truncated BOCPD. max_run caps the number of active run-length hypotheses."""
    T = len(data)
    hazard = 1.0 / hazard_lambda

    log_R = np.array([0.0])
    mu = np.array([mu0])
    kappa = np.array([kappa0])
    alpha = np.array([alpha0])
    beta = np.array([beta0])

    cp_probs = np.zeros(T)

    for t in range(T):
        x = data[t]
        n = len(log_R)
        active = np.isfinite(log_R)

        pred_scale = np.where(
            active & (alpha > 0) & (kappa > 0),
            np.sqrt(beta * (kappa + 1.0) / (alpha * kappa)),
            1.0,
        )
        pred_df = np.where(active, 2.0 * alpha, 1.0)
        log_pred = np.where(
            active,
            stats.t.logpdf(x, df=pred_df, loc=mu, scale=np.maximum(pred_scale, _EPSILON)),
            -np.inf,
        )

        log_growth = log_R + log_pred + np.log(1.0 - hazard)
        active_indices = np.where(active)[0]
        if len(active_indices) > 0:
            log_cp = (
                np.logaddexp.reduce(log_R[active_indices] + log_pred[active_indices])
                + np.log(hazard)
            )
        else:
            log_cp = -np.inf

        log_R_next = np.empty(n + 1)
        log_R_next[0] = log_cp
        log_R_next[1:] = log_growth

        # Truncate: keep at most max_run hypotheses (oldest dropped first)
        kappa_next = np.empty(n + 1)
        mu_next = np.empty(n + 1)
        alpha_next = np.empty(n + 1)
        beta_next = np.empty(n + 1)
        kappa_next[0] = kappa0
        mu_next[0] = mu0
        alpha_next[0] = alpha0
        beta_next[0] = beta0
        kappa_next[1:] = kappa + 1.0
        mu_next[1:] = (kappa * mu + x) / kappa_next[1:]
        alpha_next[1:] = alpha + 0.5
        beta_next[1:] = beta + (kappa * (x - mu) ** 2) / (2.0 * kappa_next[1:])

        if len(log_R_next) > max_run:
            log_R_next = log_R_next[:max_run]
            mu_next = mu_next[:max_run]
            kappa_next = kappa_next[:max_run]
            alpha_next = alpha_next[:max_run]
            beta_next = beta_next[:max_run]

        finite_mask = np.isfinite(log_R_next)
        if finite_mask.any():
            log_norm = np.logaddexp.reduce(log_R_next[finite_mask])
            log_R_next -= log_norm

        cp_probs[t] = float(np.exp(log_R_next[0]))
        log_R = log_R_next
        mu, kappa, alpha, beta = mu_next, kappa_next, alpha_next, beta_next

    return cp_probs


@registry.register
class BOCPDDetector(BaseDetector):
    """Bayesian Online Changepoint Detection. Score = max posterior changepoint probability in current window."""
    slug = "bocpd"
    group = "timeseries"
    min_recommended_n: ClassVar[int] = 100

    def __init__(self, hazard_lambda: float = 20.0) -> None:
        self._hazard_lambda = hazard_lambda

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu0 = float(np.mean(values))
        std0 = float(np.std(values, ddof=1))
        # max_run = half the reference length ensures old-regime hypotheses are
        # pruned when a new regime begins, enabling reliable detection.
        max_run = max(10, len(values) // 2)
        return {
            "ref_mean": mu0,
            "ref_std": max(std0, 1e-8),
            "mu0": mu0,
            "kappa0": 1.0,
            "alpha0": 1.0,
            "beta0": max(std0 ** 2, 1e-8),
            "hazard_lambda": self._hazard_lambda,
            "reference": values,
            "max_run": max_run,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr_values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr_values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={
                    "max_changepoint_prob": 0.0,
                    "ref_mean": state["ref_mean"],
                    "ref_std": state["ref_std"],
                },
            )
        # Run on combined stream; report max cp_prob in the current portion.
        combined = np.concatenate([state["reference"], curr_values])
        n_ref = len(state["reference"])
        cp_probs = _bocpd_run(
            combined,
            mu0=state["mu0"],
            kappa0=state["kappa0"],
            alpha0=state["alpha0"],
            beta0=state["beta0"],
            hazard_lambda=state["hazard_lambda"],
            max_run=state["max_run"],
        )
        curr_cp_probs = cp_probs[n_ref:]
        max_prob = float(np.max(curr_cp_probs)) if len(curr_cp_probs) > 0 else 0.0
        score = float(min(max(max_prob, 0.0), 1.0))
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"BOCPD max changepoint probability = {score:.4f} "
                f"({'changepoint likely' if score >= 0.50 else 'stable'})"
            ),
            details={
                "max_changepoint_prob": score,
                "ref_mean": state["ref_mean"],
                "ref_std": state["ref_std"],
            },
        )

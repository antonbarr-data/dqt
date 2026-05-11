# packages/dqt/src/dqt/algorithms/timeseries/page_hinkley.py
# Ref: Hinkley (1971) Biometrika 58(3) — Inference about the change-point from cumulative sum tests
# PH_t = Σ(xi - µ_ref - δ); alarm when PH_t - min(PH) > λ
# Score = (PH_current - min_PH) / λ; normalised so score=1.0 at the alarm boundary.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


@registry.register
class PageHinkleyDetector(BaseDetector):
    """Page-Hinkley online change-point detector. Score = normalised PH statistic."""
    slug = "page_hinkley"
    group = "timeseries"

    def __init__(self, delta: float = 0.005, lambda_: float = 100.0) -> None:
        self._delta = delta
        self._lambda = lambda_

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu = float(np.mean(values))
        sigma = float(np.std(values, ddof=1))
        delta_scaled = self._delta * max(sigma, _EPSILON)
        lambda_scaled = self._lambda * max(sigma, _EPSILON)
        return {
            "ref_mean": mu,
            "ref_std": max(sigma, _EPSILON),
            "delta": delta_scaled,
            "lambda": lambda_scaled,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu = state["ref_mean"]
        delta = state["delta"]
        lam = state["lambda"]
        if len(values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"ph_statistic": 0.0, "lambda_threshold": lam, "ref_mean": mu},
            )
        ph = 0.0
        ph_min = 0.0
        for x in values:
            ph += (x - mu - delta)
            ph_min = min(ph_min, ph)
        alarm_stat = max(0.0, ph - ph_min)
        score = alarm_stat / lam if lam > 0 else 0.0
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Page-Hinkley statistic = {alarm_stat:.3f} / λ={lam:.3f} → score={score:.3f} "
                f"({'alarm' if score >= 0.5 else 'normal'})"
            ),
            details={"ph_statistic": alarm_stat, "lambda_threshold": lam, "ref_mean": mu},
        )

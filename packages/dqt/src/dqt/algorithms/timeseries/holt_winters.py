# packages/dqt/src/dqt/algorithms/timeseries/holt_winters.py
# Ref: Holt (1957) ONR Memorandum 52; Winters (1960) Management Science 6(3)
# Fit additive Holt-Winters on reference; score = fraction of current values outside PI.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class HoltWintersDetector(BaseDetector):
    """Holt-Winters exponential smoothing anomaly detector. Score = fraction outside prediction interval."""
    slug = "holt_winters"
    group = "timeseries"

    def __init__(self, period: int = 7, alpha: float = 0.99) -> None:
        self._period = period
        self._alpha = alpha

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(values) < 2 * self._period:
            raise ValueError(
                f"HoltWinters requires at least {2 * self._period} observations, got {len(values)}"
            )
        model = ExponentialSmoothing(
            values,
            trend="add",
            seasonal="add",
            seasonal_periods=self._period,
            initialization_method="estimated",
        ).fit(optimized=True)
        fitted = model.fittedvalues
        residuals = values - fitted
        resid_std = float(np.std(residuals, ddof=1))
        return {
            "model": model,
            "resid_std": max(resid_std, 1e-8),
            "period": self._period,
            "alpha": self._alpha,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        from scipy import stats as scipy_stats
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"anomaly_fraction": 0.0, "n_anomalies": 0, "period": state["period"]},
            )
        model = state["model"]
        n = len(values)
        forecast = model.forecast(n)
        z = scipy_stats.norm.ppf((1.0 + state["alpha"]) / 2.0)
        margin = z * state["resid_std"]
        lower = forecast - margin
        upper = forecast + margin
        anomalies = (values < lower) | (values > upper)
        n_anomalies = int(np.sum(anomalies))
        frac = n_anomalies / n
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{n_anomalies} of {n} current values outside {state['alpha']:.0%} "
                f"Holt-Winters prediction interval ({frac:.1%})"
            ),
            details={"anomaly_fraction": frac, "n_anomalies": n_anomalies, "period": state["period"]},
        )

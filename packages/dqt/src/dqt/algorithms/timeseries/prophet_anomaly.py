# Ref: Cleveland et al. (1990) JASA — Seasonal-Trend decomposition using Loess (STL)
# STL-based replacement for Prophet backend (CmdStan not available on all platforms).
# Same slug and interface as the original ProphetAnomalyDetector.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry
from dqt.algorithms.timeseries.stl import _auto_period


@registry.register
class ProphetAnomalyDetector(BaseDetector):
    """STL-based anomaly detector with Prophet-compatible interface.
    Fits STL on the reference window to learn noise statistics, then scores the current
    window by checking what fraction of residuals exceed the prediction interval.
    """
    slug = "prophet_anomaly"
    group = "timeseries"

    def __init__(self, interval_width: float = 0.95, period: int | None = None) -> None:
        self._interval_width = interval_width
        self._period = period

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from statsmodels.tsa.seasonal import STL
        import scipy.stats
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        period = self._period if self._period is not None else _auto_period(values)
        min_len = 2 * period + 1
        if len(values) < min_len:
            raise ValueError(f"prophet_anomaly requires at least {min_len} observations for period={period}, got {len(values)}")
        result = STL(values, period=period, robust=True).fit()
        resid = result.resid
        resid_std = float(np.std(resid, ddof=1))
        z_threshold = float(scipy.stats.norm.ppf((1.0 + self._interval_width) / 2.0))
        return {
            "resid_mean": float(np.mean(resid)),
            "resid_std": resid_std if resid_std > 0 else 1.0,
            "period": period,
            "interval_width": self._interval_width,
            "z_threshold": z_threshold,
            "n_train": len(values),
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        from statsmodels.tsa.seasonal import STL
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        n = len(values)
        min_len = 2 * state["period"] + 1
        if n < min_len:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english=f"Too few observations ({n}) for STL period {state['period']}; skipping anomaly check",
                details={"n_scored": n, "period": state["period"]},
            )
        result = STL(values, period=state["period"], robust=True).fit()
        resid = result.resid
        z_scores = np.abs((resid - state["resid_mean"]) / state["resid_std"])
        anomalies = z_scores > state["z_threshold"]
        n_anomalies = int(np.sum(anomalies))
        frac = n_anomalies / n
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{n_anomalies} of {n} values outside STL "
                f"{state['interval_width']:.0%} prediction interval ({frac:.1%})"
            ),
            details={
                "anomaly_fraction": frac,
                "n_anomalies": n_anomalies,
                "z_threshold": state["z_threshold"],
                "period": state["period"],
            },
        )

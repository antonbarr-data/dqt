# Ref: Cleveland et al. (1990) JASA — Seasonal-Trend decomposition using Loess (STL)
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class STLAnomalyDetector(BaseDetector):
    """Detects anomalies via STL residuals. Score = max absolute Z-score of residuals."""
    slug = "stl_residual_zscore"
    group = "timeseries"

    def __init__(self, period: int = 7) -> None:
        self._period = period

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from statsmodels.tsa.seasonal import STL
        values = reference.iloc[:, 0].to_numpy(dtype=float)
        min_len = 2 * self._period + 1
        if len(values) < min_len:
            raise ValueError(f"STL requires at least {min_len} observations, got {len(values)}")
        result = STL(values, period=self._period, robust=True).fit()
        resid = result.resid
        resid_std = float(np.std(resid, ddof=1))
        return {
            "resid_mean": float(np.mean(resid)),
            "resid_std": resid_std if resid_std > 0 else 1.0,
            "period": self._period,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        from statsmodels.tsa.seasonal import STL
        values = current.iloc[:, 0].to_numpy(dtype=float)
        min_len = 2 * state["period"] + 1
        if len(values) < min_len:
            raise ValueError(f"STL requires at least {min_len} observations, got {len(values)}")
        result = STL(values, period=state["period"], robust=True).fit()
        resid = result.resid
        z_scores = np.abs((resid - state["resid_mean"]) / state["resid_std"])
        max_z = float(np.max(z_scores)) if len(z_scores) > 0 else 0.0
        n_anomalies = int(np.sum(z_scores > 3.0))
        return DetectorResult(
            score=max_z,
            verdict=self._verdict(max_z),
            plain_english=f"Max STL residual Z-score {max_z:.2f} ({n_anomalies} anomalous point{'s' if n_anomalies != 1 else ''})",
            details={"max_z_score": max_z, "anomaly_count": n_anomalies, "period": state["period"]},
        )

# Ref: Cleveland et al. (1990) JASA — Seasonal-Trend decomposition using Loess (STL)
from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


def _auto_period(values: np.ndarray, min_period: int = 2, max_period: int = 365) -> int:
    """Detect dominant seasonality period via FFT. Falls back to 7 if no dominant period found."""
    n = len(values)
    effective_max = max_period if n >= 2 * max_period else min(max_period, n // 4)
    if effective_max < min_period:
        return 7
    fft_vals = np.abs(np.fft.rfft(values - values.mean()))
    freqs = np.fft.rfftfreq(n)
    fft_vals[0] = 0.0  # exclude DC
    with np.errstate(divide="ignore", invalid="ignore"):
        periods = np.where(freqs > 0, 1.0 / freqs, 0.0)
    valid = (freqs > 0) & (periods >= min_period) & (periods <= effective_max)
    if not np.any(valid):
        return 7
    fft_valid = np.where(valid, fft_vals, 0.0)
    dominant_freq = freqs[np.argmax(fft_valid)]
    if dominant_freq <= 0:
        return 7
    period = int(round(1.0 / dominant_freq))
    return max(min_period, min(period, effective_max))


@registry.register
class STLAnomalyDetector(BaseDetector):
    """Detects anomalies via STL residuals. Score = max absolute Z-score of residuals."""
    slug = "stl_residual_zscore"
    group = "timeseries"
    min_recommended_n: ClassVar[int] = 100

    def __init__(self, period: int | None = None) -> None:
        self._period = period

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from statsmodels.tsa.seasonal import STL
        values = reference.iloc[:, 0].to_numpy(dtype=float)
        period = self._period if self._period is not None else _auto_period(values)
        min_len = 2 * period + 1
        if len(values) < min_len:
            raise ValueError(f"STL requires at least {min_len} observations, got {len(values)}")
        result = STL(values, period=period, robust=True).fit()
        resid = result.resid
        resid_std = float(np.std(resid, ddof=1))
        return {
            "resid_mean": float(np.mean(resid)),
            "resid_std": resid_std if resid_std > 0 else 1.0,
            "period": period,
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
        anomaly_mask = z_scores > 3.0
        n_anomalies = int(np.sum(anomaly_mask))
        anomaly_indices = [int(i) for i in np.where(anomaly_mask)[0]]
        _first = f" at index {anomaly_indices[0]}" if anomaly_indices else ""
        return DetectorResult(
            score=max_z,
            verdict=self._verdict(max_z),
            plain_english=f"Max STL residual Z={max_z:.2f}{_first} ({n_anomalies} anomalous point{'s' if n_anomalies != 1 else ''} of {len(values)})",
            details={
                "max_z_score": max_z,
                "anomaly_count": n_anomalies,
                "anomaly_indices": anomaly_indices,
                "period": state["period"],
            },
        )

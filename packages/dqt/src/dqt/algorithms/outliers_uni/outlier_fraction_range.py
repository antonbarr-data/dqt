# Tracks the fraction of outliers from an upstream detector over time.
# Learns the expected range from history and alerts when the current fraction deviates.
# No external reference — range methods are standard: IQR (Tukey 1977), percentile, z-score.
# When called on raw warehouse column data (no pre-computed outlier_fraction), computes IQR
# outlier fraction directly and compares reference vs current windows.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


def _iqr_outlier_fraction(values: np.ndarray, k: float = 1.5) -> float:
    """Fraction of values outside IQR fences [Q1 - k*IQR, Q3 + k*IQR]."""
    q1 = float(np.percentile(values, 25))
    q3 = float(np.percentile(values, 75))
    iqr = q3 - q1
    return float(np.mean((values < q1 - k * iqr) | (values > q3 + k * iqr)))


@registry.register
class OutlierFractionRangeDetector(BaseDetector):
    """Alerts when the outlier fraction deviates from the baseline.
    Accepts either a pre-computed 'outlier_fraction' series (meta-detector mode)
    or raw numeric column data (single-window mode, computes IQR fraction inline).
    """
    slug = "outlier_fraction_drift"
    group = "outliers_uni"
    kind = "sample"

    def __init__(
        self,
        method: str = "iqr",
        k: float = 1.5,
        lower_pct: float = 5.0,
        upper_pct: float = 95.0,
    ) -> None:
        if method not in ("iqr", "percentile", "zscore"):
            raise ValueError(f"Unknown method '{method}'. Use 'iqr', 'percentile', or 'zscore'.")
        self._method = method
        self._k = float(k)
        self._lower_pct = float(lower_pct)
        self._upper_pct = float(upper_pct)

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        if "outlier_fraction" not in reference.columns:
            # Raw column data mode: compute IQR fraction from the reference window
            values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
            if len(values) < 10:
                raise ValueError("outlier_fraction_drift requires at least 10 values in the reference window")
            frac = _iqr_outlier_fraction(values, self._k)
            # Allow up to 2x the baseline fraction before flagging (min 5% tolerance)
            upper = min(1.0, max(frac * 2.0, frac + 0.05))
            return {
                "mean": frac, "std": 0.0,
                "lower": 0.0, "upper": upper,
                "method": "iqr", "k": self._k,
                "n_history": 1, "raw_mode": True,
                "reference_fraction": frac,
            }

        # Meta-detector mode: reference has a pre-computed 'outlier_fraction' column
        values = reference["outlier_fraction"].dropna().to_numpy(dtype=float)
        if len(values) < 3:
            raise ValueError("outlier_fraction_drift requires at least 3 history points.")

        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0

        if self._method == "iqr":
            q1 = float(np.percentile(values, 25))
            q3 = float(np.percentile(values, 75))
            iqr = q3 - q1
            lower = q1 - self._k * iqr
            upper = q3 + self._k * iqr
        elif self._method == "percentile":
            lower = float(np.percentile(values, self._lower_pct))
            upper = float(np.percentile(values, self._upper_pct))
        else:  # zscore
            lower = mean - self._k * std
            upper = mean + self._k * std

        return {
            "mean": mean,
            "std": std,
            "lower": max(0.0, lower),
            "upper": min(1.0, upper),
            "method": self._method,
            "k": self._k,
            "n_history": len(values),
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        if "outlier_fraction" not in current.columns:
            # Raw column data mode
            values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
            if len(values) == 0:
                from dqt.algorithms._base import Verdict
                return DetectorResult(score=0.0, verdict=Verdict.pass_,
                                      plain_english="No data to score.", details={})
            current_fraction = _iqr_outlier_fraction(values, state.get("k", self._k))
        else:
            non_null = current["outlier_fraction"].dropna()
            if len(non_null) == 0:
                raise ValueError("outlier_fraction_drift: current data has no non-NaN outlier_fraction values")
            current_fraction = float(non_null.iloc[0])
        lower: float = state["lower"]
        upper: float = state["upper"]
        range_width = upper - lower

        if range_width < 1e-6:
            score = 0.0 if abs(current_fraction - upper) < 1e-6 else 1.0
        else:
            if lower <= current_fraction <= upper:
                score = 0.0
            elif current_fraction < lower:
                score = (lower - current_fraction) / range_width
            else:
                score = (current_fraction - upper) / range_width
            score = min(score, 1.0)

        verdict = self._verdict(score)

        if score == 0.0:
            plain = f"Outlier fraction {current_fraction:.3f} is within expected range [{lower:.3f}, {upper:.3f}]"
        else:
            plain = (
                f"Outlier fraction {current_fraction:.3f} is outside expected range "
                f"[{lower:.3f}, {upper:.3f}] (drift score {score:.4f})"
            )

        return DetectorResult(
            score=score,
            verdict=verdict,
            plain_english=plain,
            details={
                "current_fraction": current_fraction,
                "lower": lower,
                "upper": upper,
                "range_width": range_width,
                "method": state["method"],
                "n_history": state["n_history"],
            },
        )

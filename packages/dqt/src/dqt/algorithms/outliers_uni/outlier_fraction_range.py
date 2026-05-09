# Tracks the fraction of outliers from an upstream detector over time.
# Learns the expected range from history and alerts when the current fraction deviates.
# No external reference — range methods are standard: IQR (Tukey 1977), percentile, z-score.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class OutlierFractionRangeDetector(BaseDetector):
    """Meta-detector: alerts when the outlier fraction from an upstream detector drifts outside its historical range."""
    slug = "outlier_fraction_drift"
    group = "outliers_uni"
    kind = "sample"

    def fit(self, reference: pd.DataFrame, **params) -> DetectorState:
        """
        reference: DataFrame with a single column "outlier_fraction" (floats in [0, 1]).
        params:
            method: "iqr" | "percentile" | "zscore"  (default: "iqr")
            k: float — IQR multiplier or z-score threshold (default: 1.5)
            lower_pct: float — lower percentile for method="percentile" (default: 5.0)
            upper_pct: float — upper percentile for method="percentile" (default: 95.0)
        """
        method: str = params.get("method", "iqr")
        k: float = float(params.get("k", 1.5))
        lower_pct: float = float(params.get("lower_pct", 5.0))
        upper_pct: float = float(params.get("upper_pct", 95.0))

        values = reference["outlier_fraction"].dropna().to_numpy(dtype=float)
        if len(values) < 3:
            raise ValueError("OutlierFractionRangeDetector requires at least 3 history points.")

        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0

        if method == "iqr":
            q1 = float(np.percentile(values, 25))
            q3 = float(np.percentile(values, 75))
            iqr = q3 - q1
            lower = q1 - k * iqr
            upper = q3 + k * iqr
        elif method == "percentile":
            lower = float(np.percentile(values, lower_pct))
            upper = float(np.percentile(values, upper_pct))
        elif method == "zscore":
            lower = mean - k * std
            upper = mean + k * std
        else:
            raise ValueError(f"Unknown method '{method}'. Use 'iqr', 'percentile', or 'zscore'.")

        lower = max(0.0, lower)
        upper = min(1.0, upper)

        return {
            "mean": mean,
            "std": std,
            "lower": lower,
            "upper": upper,
            "method": method,
            "k": k,
            "n_history": len(values),
        }

    def score(self, current: pd.DataFrame, state: DetectorState, **params) -> DetectorResult:
        """
        current: DataFrame with a single column "outlier_fraction".
        Returns score = deviation from range / range width (0.0 if within range).
        """
        non_null = current["outlier_fraction"].dropna()
        if len(non_null) == 0:
            raise ValueError("OutlierFractionRangeDetector: current data has no non-NaN outlier_fraction values")
        current_fraction = float(non_null.iloc[0])
        lower: float = state["lower"]
        upper: float = state["upper"]
        range_width = upper - lower

        if range_width < 1e-6:
            # Range collapsed — history is essentially constant
            score = 0.0 if abs(current_fraction - upper) < 1e-6 else 1.0
        else:
            if lower <= current_fraction <= upper:
                score = 0.0
            elif current_fraction < lower:
                score = (lower - current_fraction) / range_width
            else:
                score = (current_fraction - upper) / range_width
            score = min(score, 1.0)  # cap to STAT_SCALE max

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

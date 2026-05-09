# Automatically selects the best univariate outlier detector by characterising
# the reference distribution first, then delegating fit+score to the chosen method.
# Selection table:
#   NORMAL          → ZScoreDetector (zscore_outlier_fraction)
#   SKEWED heavy    → DoubleMadOutlierDetector (double_mad_outlier_fraction)
#   SKEWED moderate → AdjustedBoxplotDetector (adjusted_boxplot_fraction)
#   HEAVY_TAILED    → MADOutlierDetector (mad_outlier_fraction)
#   MULTIMODAL      → MADOutlierDetector  (LOF planned Phase 2b)
#   UNIFORM         → IQR fences + needs_hitl flag
#   UNKNOWN         → MADOutlierDetector
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry
from dqt.algorithms.distribution.profiler import DistributionProfile, DistributionType, classify_distribution


def _select_slug(profile: DistributionProfile) -> str | None:
    """Return the registry slug of the best detector, or None for uniform (HITL)."""
    dt = profile.distribution_type
    if dt == DistributionType.UNIFORM:
        return None
    if dt == DistributionType.NORMAL:
        return "zscore_outlier_fraction"
    if dt == DistributionType.MULTIMODAL:
        return "mad_outlier_fraction"
    if dt in (DistributionType.SKEWED_POSITIVE, DistributionType.SKEWED_NEGATIVE):
        if abs(profile.medcouple) > 0.5 or abs(profile.skewness) > 2.0:
            return "double_mad_outlier_fraction"
        return "adjusted_boxplot_fraction"
    # HEAVY_TAILED, UNKNOWN
    return "mad_outlier_fraction"


@registry.register
class AutoOutlierDetector(BaseDetector):
    """
    Distribution-adaptive univariate outlier detector.
    Profiles the reference distribution and delegates to the optimal method.
    Uniform distributions are flagged for human review (HITL).
    """
    slug = "auto_outlier"
    group = "outliers_uni"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna()
        profile = classify_distribution(col.to_numpy(dtype=float))
        selected_slug = _select_slug(profile)

        state: dict[str, Any] = {
            "distribution_type": profile.distribution_type.value,
            "detector_slug": selected_slug,
            "is_uniform": selected_slug is None,
            "profile_skewness": profile.skewness,
            "profile_medcouple": profile.medcouple,
        }

        if selected_slug is not None:
            from dqt.algorithms._registry import registry
            cls = registry.get(selected_slug)
            inner = cls()
            state["inner_state"] = inner.fit(reference)
        else:
            q1, q3 = float(np.percentile(col, 25)), float(np.percentile(col, 75))
            iqr = q3 - q1
            state["inner_state"] = {"lower": q1 - 1.5 * iqr, "upper": q3 + 1.5 * iqr}

        return state

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        if state["is_uniform"]:
            col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
            lower = state["inner_state"]["lower"]
            upper = state["inner_state"]["upper"]
            n_out = int(np.sum((col < lower) | (col > upper)))
            outlier_frac = n_out / len(col) if len(col) > 0 else 0.0
            return DetectorResult(
                score=outlier_frac,
                verdict=Verdict.warn,
                plain_english=(
                    "Distribution appears uniform — IQR fences applied but "
                    "no statistical basis for outlier thresholds. Human review (HITL) recommended."
                ),
                details={
                    "outlier_fraction": outlier_frac,
                    "needs_hitl": True,
                    "distribution_type": state["distribution_type"],
                    "auto_selected_method": "iqr_hitl",
                },
            )

        from dqt.algorithms._registry import registry
        cls = registry.get(state["detector_slug"])
        inner = cls()
        result = inner.score(current, state["inner_state"])
        return DetectorResult(
            score=result.score,
            verdict=result.verdict,
            plain_english=result.plain_english,
            details={
                **result.details,
                "auto_selected_method": state["detector_slug"],
                "distribution_type": state["distribution_type"],
            },
        )

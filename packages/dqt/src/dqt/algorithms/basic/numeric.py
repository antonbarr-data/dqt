from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class NumericMeanDetector(BaseAggregateDetector):
    """Detects mean shift relative to baseline, expressed in standard deviations."""
    slug = "numeric_mean"
    group = "basic"

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        return [
            AggExpr(name="mean", sql=f"AVG({col})"),
            AggExpr(name="stddev", sql=f"STDDEV({col})"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        sd = float(row["stddev"] or 0)
        return {
            "ref_mean": float(row["mean"]),
            "ref_stddev": sd if sd > 0 else 1.0,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        current_mean = float(row["mean"])
        if "ref_mean" not in state:
            from dqt.algorithms._base import Verdict
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english=f"Mean={current_mean:.3g} (no baseline yet — will compare on next run)",
                details={"current_mean": current_mean},
            )
        z = abs((current_mean - state["ref_mean"]) / state["ref_stddev"])
        return DetectorResult(
            score=z,
            verdict=self._verdict(z),
            plain_english=f"Mean shifted {z:.2f}σ from baseline (baseline μ={state['ref_mean']:.3g})",
            details={"current_mean": current_mean, "baseline_mean": state["ref_mean"], "z_score": z},
        )

    def _verdict(self, score: float):
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "numeric_mean_shift")

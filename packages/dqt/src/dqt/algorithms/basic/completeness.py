from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class CompletenessDetector(BaseAggregateDetector):
    slug = "completeness"
    group = "basic"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr(name="null_count", sql=f"COUNT(*) - COUNT({col})"),
            AggExpr(name="total_count", sql="COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["null_count"]) / total) if total > 0 else 1.0
        return {"baseline_completeness": rate}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["null_count"]) / total) if total > 0 else 1.0
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=f"Completeness is {rate:.1%} (baseline {state['baseline_completeness']:.1%})",
            details={"completeness_rate": rate, "baseline": state["baseline_completeness"]},
        )

    def _verdict(self, score: float):
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "completeness_rate")

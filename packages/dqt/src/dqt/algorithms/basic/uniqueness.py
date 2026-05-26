from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class UniquenessDetector(BaseAggregateDetector):
    slug = "uniqueness"
    group = "basic"

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        return [
            AggExpr(name="distinct_count", sql=f"COUNT(DISTINCT {col})"),
            AggExpr(name="total_count", sql="COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        total = int(row["total_count"])
        rate = int(row["distinct_count"]) / total if total > 0 else 1.0
        return {"baseline_uniqueness": rate}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        rate = int(row["distinct_count"]) / total if total > 0 else 1.0
        baseline = state.get("baseline_uniqueness", rate)
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=f"Uniqueness is {rate:.1%} (baseline {baseline:.1%})",
            details={"uniqueness_rate": rate, "baseline": baseline},
        )

    def _verdict(self, score: float):
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "uniqueness_rate")

from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class CompletenessDetector(BaseAggregateDetector):
    slug = "completeness"
    group = "basic"

    def __init__(self) -> None:
        self._col: str | None = None

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        self._col = col
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
        null_count = int(row["null_count"])
        rate = 1.0 - (null_count / total) if total > 0 else 1.0
        baseline = state.get("baseline_completeness")
        plain = f"Completeness is {rate:.1%}" + (f" (baseline {baseline:.1%})" if baseline is not None else "")
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=plain,
            details={"completeness_rate": rate, "baseline": baseline},
            failing_filter_sql=f"{self._col} IS NULL" if self._col and null_count > 0 and rate < 1.0 else None,
        )

    def _verdict(self, score: float):
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "completeness_rate")

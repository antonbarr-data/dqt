from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class ValidityDetector(BaseAggregateDetector):
    slug = "validity"
    group = "basic"

    def __init__(self, sql_predicate: str = "TRUE") -> None:
        self._predicate = sql_predicate

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        return [
            AggExpr(
                name="invalid_count",
                sql=f"SUM(CASE WHEN NOT ({self._predicate}) THEN 1 ELSE 0 END)",
            ),
            AggExpr(name="total_count", sql="COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["invalid_count"]) / total) if total > 0 else 1.0
        return {"baseline_validity": rate}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["invalid_count"]) / total) if total > 0 else 1.0
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=f"{rate:.1%} of values are valid (predicate: {self._predicate!r})",
            details={"validity_rate": rate, "predicate": self._predicate},
        )

    def _verdict(self, score: float):
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "validity_rate")

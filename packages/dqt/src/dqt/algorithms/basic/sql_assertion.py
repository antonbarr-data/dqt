from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class SqlAssertionDetector(BaseAggregateDetector):
    """Custom SQL row-level condition. Score = fraction of rows where condition is FALSE.
    Dataplex parity: SqlAssertion rule. The condition is a trusted SQL expression (config-time).
    """
    slug = "sql_assertion_violation"
    group = "basic"

    def __init__(self, condition: str) -> None:
        self._condition = condition

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN NOT ({self._condition}) THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        violations = int(row["violation_count"])
        frac = violations / total if total > 0 else 0.0
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{violations}/{total} rows fail: {self._condition}",
            details={"violations": violations, "total": total, "condition": self._condition},
        )

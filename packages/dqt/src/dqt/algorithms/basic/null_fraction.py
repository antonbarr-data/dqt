from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class NullFractionDetector(BaseAggregateDetector):
    """Fraction of rows where the column is NULL.
    Dataplex parity: NullCheck rule. Complements CompletenessDetector (1 - null_fraction).
    """
    slug = "null_fraction"
    group = "basic"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("null_count", f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        null_count = int(row["null_count"])
        frac = null_count / total if total > 0 else 0.0
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{null_count}/{total} rows are NULL ({frac:.1%})",
            details={"null_count": null_count, "total_count": total},
        )

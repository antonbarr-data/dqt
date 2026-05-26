# packages/dqt/src/dqt/algorithms/referential/referential.py
# Checks that FK values in the child table exist in the parent table.
# The runner must supply a pre-computed aggregate: orphan_count + total_count.
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class ReferentialIntegrityDetector(BaseAggregateDetector):
    """
    get_aggregations() must be called with the FK column expression that already joins to the
    parent table. The caller supplies a `parent_table` and `parent_col` in params; the runner
    substitutes them into the SQL.
    """
    slug = "referential_integrity_rate"
    group = "referential"

    def __init__(self, parent_table: str, parent_col: str = "id") -> None:
        self._parent_table = parent_table
        self._parent_col = parent_col

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        return [
            AggExpr(
                name="orphan_count",
                sql=(
                    f"SUM(CASE WHEN {col} IS NOT NULL AND {col} NOT IN "
                    f"(SELECT {self._parent_col} FROM {self._parent_table}) THEN 1 ELSE 0 END)"
                ),
            ),
            AggExpr(name="total_count", sql=f"COUNT({col})"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        orphans = int(row["orphan_count"])
        rate = 1.0 - (orphans / total) if total > 0 else 1.0
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=f"Referential integrity {rate:.2%} ({orphans:,} orphan rows out of {total:,})",
            details={"integrity_rate": rate, "orphan_count": orphans, "total_count": total},
        )

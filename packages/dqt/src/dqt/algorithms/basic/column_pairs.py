from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry
from dqt.algorithms.basic._helpers import fraction_result

_ALLOWED_OPS = {">", ">=", "<", "<=", "=", "!="}


@registry.register
class ColumnPairComparisonDetector(BaseAggregateDetector):
    """
    Verifies col_a <operator> col_b for every non-null row.
    Supported operators: >, >=, <, <=, =, !=
    Score: fraction of rows where the comparison is false.
    """
    slug = "column_pair_comparison"
    group = "basic"

    def __init__(self, col_a: str = "a", col_b: str = "b", operator: str = ">") -> None:
        if operator not in _ALLOWED_OPS:
            raise ValueError(f"operator must be one of {_ALLOWED_OPS}")
        self._col_a, self._col_b, self._op = col_a, col_b, operator

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN NOT ({self._col_a} {self._op} {self._col_b}) THEN 1 ELSE 0 END)"),
            AggExpr("total_count",
                    f"SUM(CASE WHEN {self._col_a} IS NOT NULL AND {self._col_b} IS NOT NULL THEN 1 ELSE 0 END)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        label = f"{self._col_a} {self._op} {self._col_b}"
        return fraction_result(current, "column_pair_violation", label)


@registry.register
class CompositeUniquenessDetector(BaseAggregateDetector):
    """
    Verifies that the combination of key_columns forms a unique key.
    Score: fraction of rows that are duplicates.
    """
    slug = "composite_uniqueness"
    group = "basic"

    def __init__(self, key_columns: list[str] = ()) -> None:
        if not key_columns:
            raise ValueError("key_columns must be non-empty")
        self._cols = list(key_columns)

    def get_aggregations(self, col: str) -> list[AggExpr]:
        concat_expr = " || '|' || ".join(f"COALESCE({c}::text, '__null__')" for c in self._cols)
        return [
            AggExpr("total_count", "COUNT(*)"),
            AggExpr("distinct_count", f"COUNT(DISTINCT ({concat_expr}))"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        from dqt.algorithms._base import compute_verdict
        row = current.iloc[0]
        total = int(row["total_count"])
        distinct = int(row["distinct_count"])
        dup_frac = (total - distinct) / total if total > 0 else 0.0
        return DetectorResult(
            score=dup_frac,
            verdict=compute_verdict(dup_frac, "composite_uniqueness_violation"),
            plain_english=f"{dup_frac:.2%} duplicate rows on composite key {self._cols} ({total - distinct} dups)",
            details={"duplicate_fraction": dup_frac, "total": total, "distinct": distinct,
                     "key_columns": self._cols},
        )

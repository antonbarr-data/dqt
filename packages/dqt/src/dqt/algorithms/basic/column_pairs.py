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

    def __init__(
        self,
        col_a: str = "a",
        col_b: str = "b",
        operator: str = ">",
        expression: str | None = None,
    ) -> None:
        if expression:
            self._expression: str | None = expression
            self._col_a = self._col_b = self._op = ""
        else:
            if operator not in _ALLOWED_OPS:
                raise ValueError(f"operator must be one of {_ALLOWED_OPS}")
            self._col_a, self._col_b, self._op = col_a, col_b, operator
            self._expression = None

    def _condition(self) -> str:
        return self._expression or f"{self._col_a} {self._op} {self._col_b}"

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        cond = self._condition()
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN NOT ({cond}) THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return fraction_result(current, "column_pair_violation", self._condition())


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

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        if dialect == "clickhouse":
            parts = [f"COALESCE(toString({c}), '__null__')" for c in self._cols]
        elif dialect == "bigquery":
            parts = [f"COALESCE(CAST({c} AS STRING), '__null__')" for c in self._cols]
        else:
            parts = [f"COALESCE(CAST({c} AS TEXT), '__null__')" for c in self._cols]
        concat_expr = " || '|' || ".join(parts)
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

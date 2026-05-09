from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry

_ALLOWED_CASES = {"upper", "lower", "title"}


@registry.register
class StringCaseDetector(BaseAggregateDetector):
    """Validates string column casing: upper / lower / title (INITCAP).
    Dataplex parity: StringLengthCheck (case variant).
    Score: fraction of non-null rows with wrong case.
    """
    slug = "string_case_violation"
    group = "basic"

    def __init__(self, case: str = "upper") -> None:
        if case not in _ALLOWED_CASES:
            raise ValueError(f"case must be one of {_ALLOWED_CASES}, got '{case}'")
        self._case = case

    def get_aggregations(self, col: str) -> list[AggExpr]:
        if self._case == "upper":
            cond = f"{col} <> UPPER({col})"
        elif self._case == "lower":
            cond = f"{col} <> LOWER({col})"
        else:
            cond = f"{col} <> INITCAP({col})"
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} IS NOT NULL AND {cond} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", f"SUM(CASE WHEN {col} IS NOT NULL THEN 1 ELSE 0 END)"),
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
            plain_english=f"{violations}/{total} rows have wrong case (expected {self._case})",
            details={"violations": violations, "total": total, "expected_case": self._case},
        )

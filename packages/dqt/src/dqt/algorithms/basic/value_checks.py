from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


def _fraction_result(df: pd.DataFrame, slug: str, label: str) -> DetectorResult:
    from dqt.algorithms._base import compute_verdict
    row = df.iloc[0]
    total = int(row["total_count"])
    frac = int(row["violation_count"]) / total if total > 0 else 0.0
    return DetectorResult(
        score=frac,
        verdict=compute_verdict(frac, slug),
        plain_english=f"{frac:.2%} of values violate {label}",
        details={"violation_fraction": frac, "violation_count": int(row["violation_count"]), "total": total},
    )


@registry.register
class ValueInRangeDetector(BaseAggregateDetector):
    """Fraction of values outside [min_val, max_val]."""
    slug = "value_in_range"
    group = "basic"

    def __init__(self, min_val: float = float("-inf"), max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} < {self._min} OR {col} > {self._max} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "value_in_range_violation", f"range [{self._min}, {self._max}]")


@registry.register
class SetMembershipDetector(BaseAggregateDetector):
    """Fraction of values not in the allowed set."""
    slug = "set_membership"
    group = "basic"

    def __init__(self, allowed_values: set | list = ()) -> None:
        self._allowed = set(allowed_values)

    def _in_clause(self) -> str:
        quoted = ", ".join(f"'{v}'" for v in sorted(self._allowed))
        return f"({quoted})"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} NOT IN {self._in_clause()} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "set_membership_violation", f"allowed set {sorted(self._allowed)}")


@registry.register
class SetExclusionDetector(BaseAggregateDetector):
    """Fraction of values in the forbidden set."""
    slug = "set_exclusion"
    group = "basic"

    def __init__(self, forbidden_values: set | list = ()) -> None:
        self._forbidden = set(forbidden_values)

    def _in_clause(self) -> str:
        quoted = ", ".join(f"'{v}'" for v in sorted(self._forbidden))
        return f"({quoted})"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} IN {self._in_clause()} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "set_exclusion_violation", f"forbidden set {sorted(self._forbidden)}")


@registry.register
class RegexMatchDetector(BaseAggregateDetector):
    """Fraction of values not matching the regex pattern (Postgres ~ operator)."""
    slug = "regex_match"
    group = "basic"

    def __init__(self, pattern: str = ".*") -> None:
        self._pattern = pattern

    def get_aggregations(self, col: str) -> list[AggExpr]:
        escaped = self._pattern.replace("'", "''")
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col}::text !~ '{escaped}' THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "regex_match_violation", f"pattern '{self._pattern}'")


@registry.register
class StringLengthRangeDetector(BaseAggregateDetector):
    """Fraction of values with string length outside [min_len, max_len]."""
    slug = "string_length_range"
    group = "basic"

    def __init__(self, min_len: int = 0, max_len: int = 255) -> None:
        self._min, self._max = min_len, max_len

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN LENGTH({col}::text) < {self._min} OR LENGTH({col}::text) > {self._max} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "string_length_violation", f"length [{self._min}, {self._max}]")


@registry.register
class DateFormatDetector(BaseAggregateDetector):
    """Fraction of values not parseable as the given date format (Postgres TO_DATE)."""
    slug = "date_format"
    group = "basic"

    def __init__(self, date_format: str = "YYYY-MM-DD") -> None:
        self._pg_format = (date_format
                           .replace("%Y", "YYYY").replace("%m", "MM").replace("%d", "DD")
                           .replace("%H", "HH24").replace("%M", "MI").replace("%S", "SS"))

    def get_aggregations(self, col: str) -> list[AggExpr]:
        fmt = self._pg_format.replace("'", "''")
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN {col} IS NOT NULL AND "
                    f"(CASE WHEN {col}::text ~ '^[0-9]' THEN "
                    f"(SELECT COUNT(*) FROM (SELECT TO_DATE({col}::text, '{fmt}')) t) = 0 "
                    f"ELSE TRUE END) THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "date_format_violation", f"format '{self._pg_format}'")

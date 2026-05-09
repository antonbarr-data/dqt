from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry
from dqt.algorithms.basic._helpers import fraction_result


@registry.register
class ValueInRangeDetector(BaseAggregateDetector):
    """Fraction of values outside [min_val, max_val]."""
    slug = "value_in_range"
    group = "basic"

    def __init__(self, min_val: float = float("-inf"), max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val
        self._col: str | None = None

    def get_aggregations(self, col: str) -> list[AggExpr]:
        self._col = col
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} < {self._min} OR {col} > {self._max} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        result = fraction_result(current, "value_in_range_violation", f"range [{self._min}, {self._max}]")
        if self._col and result.score > 0:
            result.failing_filter_sql = f"({self._col} < {self._min} OR {self._col} > {self._max})"
        return result


@registry.register
class SetMembershipDetector(BaseAggregateDetector):
    """Fraction of values not in the allowed set."""
    slug = "set_membership"
    group = "basic"

    def __init__(self, allowed_values: set | list = ()) -> None:
        if not allowed_values:
            raise ValueError("allowed_values must be non-empty")
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
        return fraction_result(current, "set_membership_violation", f"allowed set {sorted(self._allowed)}")


@registry.register
class SetExclusionDetector(BaseAggregateDetector):
    """Fraction of values in the forbidden set."""
    slug = "set_exclusion"
    group = "basic"

    def __init__(self, forbidden_values: set | list = ()) -> None:
        if not forbidden_values:
            raise ValueError("forbidden_values must be non-empty")
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
        return fraction_result(current, "set_exclusion_violation", f"forbidden set {sorted(self._forbidden)}")


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
        return fraction_result(current, "regex_match_violation", f"pattern '{self._pattern}'")


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
        return fraction_result(current, "string_length_violation", f"length [{self._min}, {self._max}]")


@registry.register
class DateFormatDetector(BaseAggregateDetector):
    """Fraction of non-null values whose string form does not match the date format's regex structure.
    Uses structural regex matching (e.g. YYYY-MM-DD → ^\\d{4}-\\d{2}-\\d{2}$).
    For calendar-valid date checks, use ValidityDetector with a cast predicate.
    """
    slug = "date_format"
    group = "basic"

    _FORMAT_TO_REGEX: dict[str, str] = {
        "%Y": r"\d{4}", "%m": r"\d{2}", "%d": r"\d{2}",
        "%H": r"\d{2}", "%M": r"\d{2}", "%S": r"\d{2}",
        "YYYY": r"\d{4}", "MM": r"\d{2}", "DD": r"\d{2}",
        "HH24": r"\d{2}", "MI": r"\d{2}", "SS": r"\d{2}",
    }

    def __init__(self, date_format: str = "%Y-%m-%d") -> None:
        self._date_format = date_format
        self._regex = self._format_to_regex(date_format)

    def _format_to_regex(self, fmt: str) -> str:
        import re
        pattern = re.escape(fmt)
        for token, rx in self._FORMAT_TO_REGEX.items():
            pattern = pattern.replace(re.escape(token), rx)
        return f"^{pattern}$"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        escaped_regex = self._regex.replace("'", "''").replace("\\", "\\\\")
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN {col} IS NOT NULL AND {col}::text !~ '{escaped_regex}' THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return fraction_result(current, "date_format_violation", f"format '{self._date_format}'")

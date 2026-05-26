from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry
from dqt.algorithms.basic._helpers import fraction_result


def _cast_to_str(col: str, dialect: str) -> str:
    if dialect == "clickhouse":
        return f"toString({col})"
    if dialect == "bigquery":
        return f"CAST({col} AS STRING)"
    return f"CAST({col} AS TEXT)"


def _regex_not_match(col_expr: str, pattern: str, dialect: str) -> str:
    escaped = pattern.replace("'", "''")
    if dialect == "bigquery":
        return f"NOT REGEXP_CONTAINS({col_expr}, r'{escaped}')"
    if dialect == "clickhouse":
        return f"NOT match({col_expr}, '{escaped}')"
    return f"NOT ({col_expr} ~ '{escaped}')"


@registry.register
class ValueInRangeDetector(BaseAggregateDetector):
    """Fraction of values outside [min_val, max_val]."""
    slug = "value_in_range"
    group = "basic"

    def __init__(self, min_value: float = float("-inf"), max_value: float = float("inf")) -> None:
        try:
            self._min = float(min_value)
            self._max = float(max_value)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"min_value and max_value must be numeric, got min={min_value!r}, max={max_value!r}"
            ) from exc
        self._col: str | None = None

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        self._col = col
        # Build conditions only for finite bounds — inf/-inf are not valid SQL literals.
        conditions = []
        if self._min != float("-inf"):
            conditions.append(f"{col} < {self._min}")
        if self._max != float("inf"):
            conditions.append(f"{col} > {self._max}")
        if not conditions:
            violation_sql = "0"
        else:
            violation_sql = f"SUM(CASE WHEN {' OR '.join(conditions)} THEN 1 ELSE 0 END)"
        return [
            AggExpr("violation_count", violation_sql),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        bounds = f"[{self._min if self._min != float('-inf') else '-∞'}, {self._max if self._max != float('inf') else '+∞'}]"
        result = fraction_result(current, "value_in_range_violation", f"range {bounds}")
        if self._col and result.score > 0:
            parts = []
            if self._min != float("-inf"):
                parts.append(f"{self._col} < {self._min}")
            if self._max != float("inf"):
                parts.append(f"{self._col} > {self._max}")
            if parts:
                result.failing_filter_sql = f"({' OR '.join(parts)})"
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

    def _quote(self, v: object) -> str:
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        if isinstance(v, (int, float)):
            return str(v)
        return f"'{v}'"

    def _in_clause(self) -> str:
        quoted = ", ".join(self._quote(v) for v in self._allowed)
        return f"({quoted})"

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
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

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
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

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        col_expr = _cast_to_str(col, dialect)
        not_match = _regex_not_match(col_expr, self._pattern, dialect)
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {not_match} THEN 1 ELSE 0 END)"),
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

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        col_expr = _cast_to_str(col, dialect)
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN LENGTH({col_expr}) < {self._min} OR LENGTH({col_expr}) > {self._max} THEN 1 ELSE 0 END)"),
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

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        col_expr = _cast_to_str(col, dialect)
        not_match = _regex_not_match(col_expr, self._regex, dialect)
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN {col} IS NOT NULL AND {not_match} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return fraction_result(current, "date_format_violation", f"format '{self._date_format}'")

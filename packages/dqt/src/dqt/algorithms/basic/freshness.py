from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class FreshnessDetector(BaseAggregateDetector):
    """Checks that the most recent row timestamp is within the specified threshold.
    score = seconds elapsed since latest timestamp (0 if data is from the future).
    Note: uses instance-level warn/fail thresholds, not the STAT_SCALES thresholds,
    since freshness SLAs vary per table.
    """
    slug = "freshness_seconds_behind"
    group = "basic"

    def __init__(self, col: str = "updated_at", warn_seconds: float = 3600, fail_seconds: float = 86400) -> None:
        self._col = col
        self._warn = warn_seconds
        self._fail = fail_seconds

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr("latest_ts", f"MAX({col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        latest = current.iloc[0]["latest_ts"]
        if hasattr(latest, "tzinfo") and latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        if not hasattr(latest, "timestamp"):
            return DetectorResult(
                score=float("inf"),
                verdict=Verdict.fail,
                plain_english="Latest timestamp could not be parsed",
                details={"seconds_behind": float("inf"), "warn_threshold": self._warn, "fail_threshold": self._fail},
            )

        seconds_behind = (now - latest).total_seconds()

        # Future timestamps are a real failure mode (sentinel values, timezone bugs, clock skew).
        if seconds_behind < 0:
            seconds_ahead = -seconds_behind
            return DetectorResult(
                score=0.0,
                verdict=Verdict.warn,
                plain_english=(
                    f"Latest timestamp is {seconds_ahead:.0f}s in the future — "
                    "possible clock skew, sentinel value, or timezone bug"
                ),
                details={
                    "seconds_behind": 0.0,
                    "seconds_ahead": seconds_ahead,
                    "data_from_future": True,
                    "warn_threshold": self._warn,
                    "fail_threshold": self._fail,
                },
            )

        if seconds_behind >= self._fail:
            verdict = Verdict.fail
        elif seconds_behind >= self._warn:
            verdict = Verdict.warn
        else:
            verdict = Verdict.pass_

        return DetectorResult(
            score=seconds_behind,
            verdict=verdict,
            plain_english=f"Latest data is {seconds_behind:.0f}s old (warn >{self._warn:.0f}s, fail >{self._fail:.0f}s)",
            details={
                "seconds_behind": seconds_behind,
                "data_from_future": False,
                "warn_threshold": self._warn,
                "fail_threshold": self._fail,
            },
        )

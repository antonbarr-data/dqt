# Base classes for all detectors. StatScale and STAT_SCALES live in _scales.py (no dqt imports there).
# compute_verdict defers the _scales import to break any potential circular dependency.
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

import pandas as pd

if TYPE_CHECKING:
    from dqt.adapters._protocol import AggExpr


class Verdict(str, Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"


@dataclass
class DetectorResult:
    score: float
    verdict: Verdict
    plain_english: str
    details: dict[str, Any] = field(default_factory=dict)
    # WHERE clause (no "WHERE" keyword) identifying failing rows; runner constructs full SQL
    failing_filter_sql: str | None = None


DetectorState = Any


def compute_verdict(
    score: float,
    slug: str,
    warn_threshold: float | None = None,
    fail_threshold: float | None = None,
) -> Verdict:
    from dqt.algorithms._scales import STAT_SCALES  # deferred to avoid circular deps
    scale = STAT_SCALES.get(slug)
    if scale is None:
        raise KeyError(f"No STAT_SCALE entry for slug '{slug}'. Add it to _scales.py.")
    warn = warn_threshold if warn_threshold is not None else scale.warn_threshold
    fail = fail_threshold if fail_threshold is not None else scale.fail_threshold
    if scale.direction == "lower_is_better":
        if score >= fail:
            return Verdict.fail
        if score >= warn:
            return Verdict.warn
        return Verdict.pass_
    else:
        if score <= fail:
            return Verdict.fail
        if score <= warn:
            return Verdict.warn
        return Verdict.pass_


class BaseDetector:
    slug: ClassVar[str]
    group: ClassVar[str]
    kind: ClassVar[str] = "sample"
    # Minimum N for reliable results. Runner prepends a low-power warning when
    # len(current_df) < min_recommended_n.
    min_recommended_n: ClassVar[int] = 30

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        raise NotImplementedError

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        raise NotImplementedError

    def _verdict(self, score: float) -> Verdict:
        return compute_verdict(score, self.slug)

    def suggest_threshold(
        self,
        reference_df: "pd.DataFrame",
        target_fpr: float = 0.001,
        n_bootstrap: int = 200,
    ) -> dict:
        """Bootstrap-calibrate a score threshold for target false-positive rate on clean data."""
        from dqt.algorithms._calibration import suggest_threshold as _suggest
        return _suggest(self, reference_df, target_fpr=target_fpr, n_bootstrap=n_bootstrap)


class BaseAggregateDetector(BaseDetector):
    kind: ClassVar[str] = "aggregate"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        raise NotImplementedError

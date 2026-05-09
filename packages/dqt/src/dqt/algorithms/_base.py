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


DetectorState = Any


def compute_verdict(score: float, slug: str) -> Verdict:
    from dqt.algorithms._scales import STAT_SCALES  # deferred to avoid circular deps
    scale = STAT_SCALES.get(slug)
    if scale is None:
        raise KeyError(f"No STAT_SCALE entry for slug '{slug}'. Add it to _scales.py.")
    if scale.direction == "lower_is_better":
        if score >= scale.fail_threshold:
            return Verdict.fail
        if score >= scale.warn_threshold:
            return Verdict.warn
        return Verdict.pass_
    else:
        if score <= scale.fail_threshold:
            return Verdict.fail
        if score <= scale.warn_threshold:
            return Verdict.warn
        return Verdict.pass_


class BaseDetector:
    slug: ClassVar[str]
    group: ClassVar[str]
    kind: ClassVar[str] = "sample"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        raise NotImplementedError

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        raise NotImplementedError

    def _verdict(self, score: float) -> Verdict:
        return compute_verdict(score, self.slug)


class BaseAggregateDetector(BaseDetector):
    kind: ClassVar[str] = "aggregate"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        raise NotImplementedError

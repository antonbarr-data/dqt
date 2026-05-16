from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4


@dataclass
class EvidenceRow:
    source: str          # "check:null_fraction" | "granger:revenue->signups"
    signal_type: str     # "failed_check" | "causal_edge" | "mix_shift" | "schema_change"
    magnitude: float     # central estimate 0.0-1.0
    magnitude_low: float
    magnitude_high: float
    evidence_strength: str  # "weak" | "moderate" | "strong"
    detail: dict[str, Any] = field(default_factory=dict)
    row_id: str = field(default_factory=lambda: str(uuid4())[:8])


@dataclass
class DataIssue:
    check_id: UUID
    detector_slug: str
    verdict: str          # "warn" | "fail"
    run_at: datetime
    contribution_low: float
    contribution_high: float
    evidence: EvidenceRow


@dataclass
class RankedCause:
    cause_metric_fqn: str
    lag_periods: int
    p_value: float
    evidence_strength: str
    contribution_low: float
    contribution_high: float
    evidence: EvidenceRow


@dataclass
class MixShiftReport:
    dimension: str
    segments: list[dict[str, Any]]  # [{segment, share_before, share_after, value_before, value_after}]
    mix_contribution_low: float
    mix_contribution_high: float
    evidence: EvidenceRow


@dataclass
class RuledOutItem:
    candidate_fqn: str
    reason: str


@dataclass
class MovementExplanation:
    metric_fqn: str
    window_start: datetime
    window_end: datetime
    observed_change: float               # signed fraction: -0.18 = 18% decline

    # Channel A -- data integrity
    data_issues: list[DataIssue]
    estimated_data_contribution: tuple[float, float]    # (low, high) in [0, 1]

    # Channel B -- business drivers
    business_drivers: list[RankedCause]
    mix_shift: MixShiftReport | None
    ruled_out: list[RuledOutItem]
    estimated_business_contribution: tuple[float, float]

    # Reconciliation
    summary_paragraph: str
    primary_channel: Literal["data", "business", "mixed"]

    # Audit -- sentence_id maps to evidence rows that produced it
    citations: dict[str, list[EvidenceRow]]
    computation_metadata: dict[str, Any] = field(default_factory=dict)
    explanation_id: UUID = field(default_factory=uuid4)

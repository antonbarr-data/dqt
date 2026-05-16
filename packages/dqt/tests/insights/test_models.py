# packages/dqt/tests/insights/test_models.py
from datetime import datetime, timezone
from uuid import uuid4
from dqt.insights.models import (
    EvidenceRow, DataIssue, RankedCause, MixShiftReport,
    RuledOutItem, MovementExplanation,
)


def _now():
    return datetime.now(timezone.utc)


def test_evidence_row_has_unique_row_id():
    a = EvidenceRow(source="check:null_fraction", signal_type="failed_check",
                    magnitude=0.15, magnitude_low=0.05, magnitude_high=0.30,
                    evidence_strength="strong")
    b = EvidenceRow(source="check:null_fraction", signal_type="failed_check",
                    magnitude=0.15, magnitude_low=0.05, magnitude_high=0.30,
                    evidence_strength="strong")
    assert a.row_id != b.row_id


def test_movement_explanation_primary_channel_valid():
    expl = MovementExplanation(
        metric_fqn="test.public.orders.revenue",
        window_start=_now(), window_end=_now(),
        observed_change=-0.18,
        data_issues=[], estimated_data_contribution=(0.0, 0.0),
        business_drivers=[], mix_shift=None, ruled_out=[],
        estimated_business_contribution=(0.0, 0.0),
        summary_paragraph="No significant drivers identified.",
        primary_channel="mixed",
        citations={},
    )
    assert expl.primary_channel in ("data", "business", "mixed")
    assert expl.estimated_data_contribution[0] <= expl.estimated_data_contribution[1]
    assert expl.estimated_business_contribution[0] <= expl.estimated_business_contribution[1]


def test_ruled_out_item():
    item = RuledOutItem(candidate_fqn="test.orders.ad_spend", reason="p_value=0.42 (not significant)")
    assert item.reason

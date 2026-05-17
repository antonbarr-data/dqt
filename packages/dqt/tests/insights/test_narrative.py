# packages/dqt/tests/insights/test_narrative.py
from datetime import datetime, timezone
from uuid import uuid4
from dqt.insights.models import (
    MovementExplanation, DataIssue, EvidenceRow, RuledOutItem,
)
from dqt.insights.narrative import generate, _template_narrative, _post_process_citations


def _base_explanation(**kwargs) -> MovementExplanation:
    now = datetime.now(timezone.utc)
    defaults = dict(
        metric_fqn="test.public.orders.revenue",
        window_start=now,
        window_end=now,
        observed_change=-0.18,
        data_issues=[],
        estimated_data_contribution=(0.0, 0.0),
        business_drivers=[],
        mix_shift=None,
        ruled_out=[RuledOutItem("test.orders.ad_spend", "p=0.42")],
        estimated_business_contribution=(0.0, 0.0),
        summary_paragraph="",
        primary_channel="mixed",
        citations={},
    )
    defaults.update(kwargs)
    return MovementExplanation(**defaults)


def test_template_narrative_no_issues():
    expl = _base_explanation()
    text = _template_narrative(expl)
    assert isinstance(text, str)
    assert len(text) > 10


def test_template_narrative_with_fail_issue():
    ev = EvidenceRow("check:null_fraction", "failed_check", 0.15, 0.05, 0.30, "strong",
                     {"score": 0.15, "plain_english": "15% null"})
    issue = DataIssue(uuid4(), "null_fraction", "fail", datetime.now(timezone.utc), 0.05, 0.30, ev)
    expl = _base_explanation(data_issues=[issue], estimated_data_contribution=(0.05, 0.30))
    text = _template_narrative(expl)
    assert "null_fraction" in text
    assert "fail" in text


def test_post_process_citations_accepts_clean_prose():
    ev = EvidenceRow("check:x", "failed_check", 0.1, 0.05, 0.2, "moderate")
    ev.row_id = "abc12345"
    evidence_by_id = {"abc12345": ev}
    text = "Revenue fell 18% [abc12345]."
    citations, ok = _post_process_citations(text, evidence_by_id)
    assert len(citations) >= 1
    assert "abc12345" in str(citations)


def test_generate_falls_back_to_template_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    expl = _base_explanation()
    result = generate(expl)
    assert isinstance(result.summary_paragraph, str)
    assert len(result.summary_paragraph) > 10

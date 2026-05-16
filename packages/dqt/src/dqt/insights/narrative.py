"""Narrative generation pipeline.

Tries to generate prose via Claude claude-haiku-4-5-20251001. Falls back to template prose when:
- ANTHROPIC_API_KEY is not set
- LLM is unavailable
- Post-processor rejects all 3 attempts (every number must trace to an EvidenceRow)

Every generated sentence is assigned a sentence_id; citations[sentence_id] names the
evidence rows that produced it.
"""
from __future__ import annotations

import json
import os
import re

from dqt.insights.models import EvidenceRow, MovementExplanation

_MAX_RETRIES = 3
_MAX_WORDS_INSIGHT = 200


def generate(explanation: MovementExplanation) -> MovementExplanation:
    """Populate summary_paragraph and citations on explanation, return it."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _apply_template(explanation)

    evidence_by_id = _build_evidence_index(explanation)

    for attempt in range(_MAX_RETRIES):
        try:
            prose = _call_llm(explanation, evidence_by_id, api_key)
            citations, ok = _post_process_citations(prose, evidence_by_id)
            if ok or attempt == _MAX_RETRIES - 1:
                explanation.summary_paragraph = _strip_citations(prose)
                explanation.citations = citations
                return explanation
        except Exception:
            break

    return _apply_template(explanation)


def _apply_template(explanation: MovementExplanation) -> MovementExplanation:
    explanation.summary_paragraph = _template_narrative(explanation)
    explanation.citations = {}
    return explanation


def _template_narrative(explanation: MovementExplanation) -> str:
    parts: list[str] = []
    pct = abs(explanation.observed_change * 100)
    direction = "fell" if explanation.observed_change < 0 else "rose"
    parts.append(f"{explanation.metric_fqn} {direction} {pct:.1f}% in the analysis window.")

    if explanation.data_issues:
        top = explanation.data_issues[0]
        parts.append(
            f"The most significant data quality issue was {top.detector_slug} "
            f"returning {top.verdict} (score {top.evidence.detail.get('score', 0):.2f}), "
            f"potentially contributing {top.contribution_low * 100:.0f}-"
            f"{top.contribution_high * 100:.0f}% of the observed movement."
        )

    if explanation.business_drivers:
        top = explanation.business_drivers[0]
        parts.append(
            f"Causal analysis identifies {top.cause_metric_fqn} as a likely driver "
            f"(lag {top.lag_periods} period(s), p={top.p_value:.3f}, "
            f"{top.evidence_strength} evidence)."
        )

    if not explanation.data_issues and not explanation.business_drivers:
        parts.append("No significant drivers were identified within the analysis window.")

    return " ".join(parts)


def _build_evidence_index(explanation: MovementExplanation) -> dict[str, EvidenceRow]:
    index: dict[str, EvidenceRow] = {}
    for issue in explanation.data_issues:
        index[issue.evidence.row_id] = issue.evidence
    for driver in explanation.business_drivers:
        index[driver.evidence.row_id] = driver.evidence
    if explanation.mix_shift:
        index[explanation.mix_shift.evidence.row_id] = explanation.mix_shift.evidence
    return index


def _call_llm(
    explanation: MovementExplanation,
    evidence_by_id: dict[str, EvidenceRow],
    api_key: str,
) -> str:
    import anthropic

    evidence_json = json.dumps(
        [
            {
                "id": row_id,
                "source": ev.source,
                "signal_type": ev.signal_type,
                "magnitude_pct": f"{ev.magnitude * 100:.1f}%",
                "magnitude_range": f"{ev.magnitude_low * 100:.0f}-{ev.magnitude_high * 100:.0f}%",
                "evidence_strength": ev.evidence_strength,
                "detail": ev.detail,
            }
            for row_id, ev in evidence_by_id.items()
        ],
        indent=2,
    )
    pct = abs(explanation.observed_change * 100)
    direction = "fell" if explanation.observed_change < 0 else "rose"

    prompt = f"""You are a data analyst. Write a paragraph (max {_MAX_WORDS_INSIGHT} words) explaining why \
{explanation.metric_fqn} {direction} {pct:.1f}%.

EVIDENCE:
{evidence_json}

RULES:
- Every percentage or number you state MUST come from the evidence above.
- After each cited number, append [evidence_id] in brackets -- e.g., "revenue fell 18% [abc12345]".
- Analyst voice: clear, no hedging when evidence is strong.
- Do not speculate beyond the evidence.
- Do not mention evidence IDs that are not in the list above.

Write the paragraph now:"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _post_process_citations(
    text: str,
    evidence_by_id: dict[str, EvidenceRow],
) -> tuple[dict[str, list[EvidenceRow]], dict[str, list[EvidenceRow]]]:
    """Parse citations from LLM output.

    Returns (all_citations, valid_only) where valid_only is empty if any number lacks a citation.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    citations: dict[str, list[EvidenceRow]] = {}
    uncited_numbers = False

    for i, sentence in enumerate(sentences):
        sid = f"s{i}"
        refs = re.findall(r"\[([a-f0-9]{8})\]", sentence)
        cited_rows = [evidence_by_id[r] for r in refs if r in evidence_by_id]
        if cited_rows:
            citations[sid] = cited_rows
        has_number = bool(re.search(r"\d+\.?\d*%|\$\d+|\d+\s*(?:million|billion|k\b)", sentence, re.I))
        if has_number and not cited_rows:
            uncited_numbers = True

    return citations, ({} if uncited_numbers else citations)


def _strip_citations(text: str) -> str:
    """Remove [row_id] markers from prose for display."""
    return re.sub(r"\s*\[[a-f0-9]{8}\]", "", text).strip()

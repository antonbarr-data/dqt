# packages/dqt/src/dqt/checks/suggest.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

_ISO3166_CODES: list[str] = []
try:
    import pycountry as _pc
    _ISO3166_CODES = [c.alpha_2 for c in _pc.countries]
except ImportError:
    _ISO3166_CODES = [
        "US", "GB", "DE", "FR", "CA", "AU", "JP", "IN", "BR", "MX",
        "CN", "KR", "SG", "NL", "SE", "NO", "DK", "FI", "CH", "ES",
        "IT", "PL", "RU", "ZA", "NG", "EG", "AR", "CL", "CO", "PE",
    ]

_NOW_SENTINEL = "__now__"


@dataclass
class ColumnProfile:
    name: str
    data_type: str
    null_fraction: float
    distinct_count: int
    sample_values: list[str]
    min_value: Any | None
    max_value: Any | None
    is_likely_pk: bool
    is_likely_fk: bool
    is_likely_enum: bool
    is_likely_email: bool
    is_likely_timestamp: bool
    is_likely_currency: bool
    is_likely_country: bool
    sample_size_used: int = 0


@dataclass
class SuggestedCheck:
    detector_slug: str
    params: dict
    rationale: str
    confidence: float
    sample_size_used: int = 0


def _is_numeric(data_type: str) -> bool:
    return any(t in data_type.lower() for t in ("int", "float", "double", "decimal", "numeric", "real"))


def _is_ts(data_type: str) -> bool:
    return any(t in data_type.lower() for t in ("timestamp", "datetime", "date", "time"))


def suggest_checks_for_column(
    profile: ColumnProfile,
    *,
    use_llm: bool = True,
) -> list[SuggestedCheck]:
    """Return ranked check suggestions for a column. Heuristic core; LLM layer is opt-in."""
    suggestions: list[SuggestedCheck] = []

    def add(slug: str, params: dict, rationale: str, confidence: float) -> None:
        suggestions.append(SuggestedCheck(
            detector_slug=slug, params=params, rationale=rationale,
            confidence=confidence, sample_size_used=profile.sample_size_used,
        ))

    # Baseline null_fraction — threshold depends on whether this is a PK
    if profile.is_likely_pk:
        add("null_fraction", {"fail_threshold": 0.0001},
            "Primary keys must be non-null; any NULL is a data issue.", 0.95)
        add("uniqueness", {}, "Primary keys must be unique across all rows.", 0.95)
    else:
        add("null_fraction", {"fail_threshold": 0.5},
            "Tracks what fraction of rows are NULL in this column.", 0.6)

    if profile.is_likely_fk:
        add("referential_integrity", {},
            f"Column name '{profile.name}' suggests a foreign key; check referential integrity.", 0.75)

    if profile.is_likely_enum and profile.sample_values:
        add("set_membership", {"allowed_values": list(profile.sample_values)},
            f"Only {profile.distinct_count} distinct values observed; flag any value outside this set.", 0.85)

    if profile.is_likely_email:
        add("regex_match", {"pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$"},
            "Column contains email addresses; validate format with regex.", 0.90)

    if profile.is_likely_timestamp or _is_ts(profile.data_type):
        add("freshness_seconds_behind", {"warn_threshold": 3600, "fail_threshold": 86400},
            "Timestamp column should be refreshed regularly; detect stale data.", 0.80)
        add("value_in_range", {"max_value": _NOW_SENTINEL},
            "Timestamp values should not be in the future.", 0.70)

    if profile.is_likely_currency:
        if profile.min_value is not None and profile.min_value < 0:
            add("value_in_range", {"min_value": 0},
                f"Column '{profile.name}' looks like an amount but has negative values; flag if unexpected.", 0.75)
        else:
            add("value_in_range", {"min_value": 0},
                "Currency columns should not be negative.", 0.65)

    if profile.is_likely_country:
        add("set_membership", {"allowed_values": _ISO3166_CODES},
            "Country codes should match ISO 3166-1 alpha-2 values.", 0.85)

    if _is_numeric(profile.data_type) and not profile.is_likely_pk and not profile.is_likely_currency:
        add("mad_outlier_fraction", {"threshold": 3.5, "warn_threshold": 0.01, "fail_threshold": 0.05},
            "Numeric columns benefit from outlier detection using MAD (robust to heavy tails).", 0.60)

    if use_llm:
        suggestions.extend(_llm_suggestions(profile))

    # Deduplicate by slug, keep highest confidence
    seen: dict[str, SuggestedCheck] = {}
    for s in sorted(suggestions, key=lambda x: x.confidence, reverse=True):
        if s.detector_slug not in seen:
            seen[s.detector_slug] = s
    return list(seen.values())


def _llm_suggestions(profile: ColumnProfile) -> list[SuggestedCheck]:
    """Semantic suggestions via LLM. No-ops gracefully if API key absent."""
    try:
        import anthropic as _anthropic
        import os as _os
        api_key = _os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return []
        client = _anthropic.Anthropic(api_key=api_key)
        prompt = (
            f"Column: {profile.name}, type: {profile.data_type}, "
            f"null_fraction: {profile.null_fraction:.3f}, "
            f"distinct_count: {profile.distinct_count}, "
            f"sample_values: {profile.sample_values[:5]}.\n"
            "Suggest at most 2 additional data quality checks that the heuristic rules would miss. "
            "Reply as JSON: [{\"detector_slug\": str, \"params\": dict, \"rationale\": str, \"confidence\": float}]. "
            "Only include checks with confidence > 0.6. Return [] if nothing to add."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        import json as _json
        raw = msg.content[0].text.strip()
        parsed = _json.loads(raw)
        return [
            SuggestedCheck(
                detector_slug=item["detector_slug"],
                params=item.get("params", {}),
                rationale=item.get("rationale", "LLM-suggested check."),
                confidence=float(item.get("confidence", 0.65)),
            )
            for item in parsed
            if isinstance(item, dict) and "detector_slug" in item
        ]
    except Exception:
        return []

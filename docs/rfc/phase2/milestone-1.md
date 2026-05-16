# Milestone 1 — Foundation, Check Suggestions, Metric Registry

> Target: v1.1.0-RC. Prerequisite for all other milestones.

## Goal

A new team can adopt dqt in an afternoon: browse their warehouse, accept AI-suggested checks per column, end up with hundreds of well-calibrated checks covering core tables. Every column with at least one check becomes a tracked metric.

## What this milestone builds

1. `dqt.checks.suggest` — heuristic + LLM-augmented check suggestion engine
2. `dqt.metrics.Metric` and `MetricRegistry` — foundation data types for M2
3. `GET /api/v1/datasets/{dataset_id}/columns/{column}/suggest` — suggestion endpoint
4. Column profile page augmented with "AI Suggestions" section and check picker
5. Metrics page archived (placeholder replacing mock dashboard)

## What this milestone does NOT build (deferred to brief's later milestones)

- `dqt metrics serve` CLI (Option A: existing server handles everything)
- Vite SPA (Option A: Next.js handles everything)
- `dqt migrate` CLI (DB schema changes done inline)
- Separate subscription tables (added incrementally in M4)
- New brand tokens (existing globals.css is the design system)

## File map

### Library (`packages/dqt/`)
- **Create** `src/dqt/checks/suggest.py` — ColumnProfile, SuggestedCheck, suggest_checks_for_column
- **Modify** `src/dqt/checks/__init__.py` — export suggest symbols
- **Create** `src/dqt/metrics/models.py` — Metric dataclass
- **Create** `src/dqt/metrics/registry.py` — MetricRegistry class
- **Modify** `src/dqt/metrics/__init__.py` — export Metric, MetricRegistry
- **Create** `tests/checks/test_suggest.py` — 30 column profile fixtures
- **Create** `tests/metrics/test_registry.py` — get/search/list/reload specs

### Server (`apps/server/`)
- **Create** `src/dqt_server/api/v1/suggest.py` — suggestion + check-attach endpoints
- **Create** `src/dqt_server/models/suggestion.py` — CheckSuggestion SQLAlchemy model
- **Modify** `src/dqt_server/main.py` — register suggest_router
- **Modify** `src/dqt_server/db/engine.py` or run inline DDL for `dqt_check_suggestions` table

### Frontend (`apps/web/`)
- **Create** `src/components/checks/suggest-panel.tsx` — client component: AI suggestions list + accept/reject
- **Create** `src/components/checks/check-picker.tsx` — client component: modal with Suggested + All tabs
- **Modify** `src/app/(app)/datasets/[id]/[column]/page.tsx` — add suggestions section + check picker trigger
- **Modify** `src/app/(app)/metrics/page.tsx` — archive with placeholder ("Metric insight page arriving in v1.1")

## Tasks

---

### Task 1: `dqt.checks.suggest` — heuristic suggestion engine

**Files:**
- Create: `packages/dqt/src/dqt/checks/suggest.py`
- Create: `packages/dqt/tests/checks/test_suggest.py`
- Modify: `packages/dqt/src/dqt/checks/__init__.py`

The library must remain importable without Postgres, Redis, or a network.
The heuristic core must never import from `dqt_server`.

**Step 1: Write failing tests**

```python
# packages/dqt/tests/checks/test_suggest.py
from dqt.checks.suggest import ColumnProfile, SuggestedCheck, suggest_checks_for_column

def _prof(**kw) -> ColumnProfile:
    defaults = dict(
        name="col", data_type="text", null_fraction=0.0, distinct_count=10,
        sample_values=[], min_value=None, max_value=None,
        is_likely_pk=False, is_likely_fk=False, is_likely_enum=False,
        is_likely_email=False, is_likely_timestamp=False,
        is_likely_currency=False, is_likely_country=False,
    )
    return ColumnProfile(**{**defaults, **kw})

def test_pk_gets_null_fraction_and_uniqueness():
    prof = _prof(name="id", data_type="integer", is_likely_pk=True, null_fraction=0.0)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "null_fraction" in slugs
    assert "uniqueness" in slugs

def test_email_gets_regex():
    prof = _prof(name="email", data_type="text", is_likely_email=True,
                 sample_values=["a@b.com", "c@d.org"])
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "regex_match" in slugs

def test_enum_gets_set_membership():
    prof = _prof(name="status", data_type="text", is_likely_enum=True, distinct_count=3,
                 sample_values=["active", "inactive", "pending"])
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "set_membership" in slugs

def test_timestamp_gets_freshness():
    prof = _prof(name="created_at", data_type="timestamp", is_likely_timestamp=True)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "freshness_seconds_behind" in slugs

def test_currency_negative_min_gets_value_in_range():
    prof = _prof(name="amount", data_type="float", is_likely_currency=True,
                 min_value=-5.0, max_value=1000.0)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "value_in_range" in slugs

def test_country_gets_set_membership_iso():
    prof = _prof(name="country_code", data_type="text", is_likely_country=True,
                 distinct_count=30, sample_values=["US", "GB", "DE"])
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "set_membership" in slugs
    # Params should include ISO 3166 codes
    sm = next(s for s in suggestions if s.detector_slug == "set_membership")
    assert "US" in sm.params.get("allowed_values", [])

def test_fk_gets_referential_integrity():
    prof = _prof(name="user_id", data_type="integer", is_likely_fk=True)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "referential_integrity" in slugs

def test_numeric_heavy_tailed_gets_mad():
    prof = _prof(name="revenue", data_type="float", distinct_count=5000,
                 min_value=0.0, max_value=1_000_000.0)
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "mad_outlier_fraction" in slugs

def test_all_columns_get_completeness_baseline():
    prof = _prof(name="any_col")
    suggestions = suggest_checks_for_column(prof, use_llm=False)
    slugs = [s.detector_slug for s in suggestions]
    assert "null_fraction" in slugs or "completeness" in slugs

def test_confidence_scores_in_range():
    prof = _prof(name="id", is_likely_pk=True)
    for s in suggest_checks_for_column(prof, use_llm=False):
        assert 0.0 <= s.confidence <= 1.0

def test_rationale_is_non_empty():
    prof = _prof(name="email", is_likely_email=True)
    for s in suggest_checks_for_column(prof, use_llm=False):
        assert s.rationale.strip()
```

**Step 2: Verify tests fail**
```
uv run pytest packages/dqt/tests/checks/test_suggest.py -v
```
Expected: all tests fail with ImportError.

**Step 3: Implement `suggest.py`**

```python
# packages/dqt/src/dqt/checks/suggest.py
# Heuristic check suggestion engine. LLM layer is opt-in via use_llm=True.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pycountry  # graceful fallback if not installed


_ISO3166_CODES: list[str] = []
try:
    import pycountry as _pc
    _ISO3166_CODES = [c.alpha_2 for c in _pc.countries]
except Exception:
    # Fallback: common subset
    _ISO3166_CODES = [
        "US", "GB", "DE", "FR", "CA", "AU", "JP", "IN", "BR", "MX",
        "CN", "KR", "SG", "NL", "SE", "NO", "DK", "FI", "CH", "ES",
        "IT", "PL", "RU", "ZA", "NG", "EG", "AR", "CL", "CO", "PE",
    ]


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
    """Return heuristic check suggestions for a column, sorted by confidence desc.
    
    use_llm=True adds a semantic pass via the Anthropic API when available.
    The heuristic core never makes network calls.
    """
    suggestions: list[SuggestedCheck] = []

    def add(slug: str, params: dict, rationale: str, confidence: float) -> None:
        suggestions.append(SuggestedCheck(
            detector_slug=slug,
            params=params,
            rationale=rationale,
            confidence=confidence,
            sample_size_used=profile.sample_size_used,
        ))

    # Baseline: every column gets null fraction check
    add(
        "null_fraction",
        {"fail_threshold": 0.5},
        "Tracks what fraction of rows are NULL in this column.",
        0.6,
    )

    # Primary key heuristics
    if profile.is_likely_pk:
        # Override null threshold to near-zero for PKs
        suggestions[-1] = SuggestedCheck(
            detector_slug="null_fraction",
            params={"fail_threshold": 0.0001},
            rationale="Primary keys must be non-null; any NULL is a data issue.",
            confidence=0.95,
            sample_size_used=profile.sample_size_used,
        )
        add("uniqueness", {}, "Primary keys must be unique across all rows.", 0.95)

    # Foreign key
    if profile.is_likely_fk:
        add(
            "referential_integrity",
            {},
            f"Column name '{profile.name}' suggests a foreign key; check referential integrity.",
            0.75,
        )

    # Enum / low-cardinality
    if profile.is_likely_enum and profile.sample_values:
        add(
            "set_membership",
            {"allowed_values": list(profile.sample_values)},
            f"Only {profile.distinct_count} distinct values observed; flag any value outside this set.",
            0.85,
        )

    # Email
    if profile.is_likely_email:
        add(
            "regex_match",
            {"pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$"},
            "Column contains email addresses; validate format with regex.",
            0.90,
        )

    # Timestamp
    if profile.is_likely_timestamp or _is_ts(profile.data_type):
        add(
            "freshness_seconds_behind",
            {"warn_threshold": 3600, "fail_threshold": 86400},
            "Timestamp column should be refreshed regularly; detect stale data.",
            0.80,
        )
        add(
            "value_in_range",
            {"max_value": "__now__"},
            "Timestamp values should not be in the future.",
            0.70,
        )

    # Currency / amount
    if profile.is_likely_currency:
        if profile.min_value is not None and profile.min_value < 0:
            add(
                "value_in_range",
                {"min_value": 0},
                f"Column '{profile.name}' looks like an amount but has negative values; flag if unexpected.",
                0.75,
            )
        else:
            add(
                "value_in_range",
                {"min_value": 0},
                f"Currency columns should not be negative.",
                0.65,
            )

    # Country code
    if profile.is_likely_country:
        add(
            "set_membership",
            {"allowed_values": _ISO3166_CODES},
            "Country codes should match ISO 3166-1 alpha-2 values.",
            0.85,
        )

    # Numeric heavy-tailed
    if _is_numeric(profile.data_type) and not profile.is_likely_pk and not profile.is_likely_currency:
        add(
            "mad_outlier_fraction",
            {"threshold": 3.5, "warn_threshold": 0.01, "fail_threshold": 0.05},
            "Numeric columns benefit from outlier detection using MAD (robust to heavy tails).",
            0.60,
        )

    # LLM augmentation (second pass, network call, cached externally)
    if use_llm:
        suggestions.extend(_llm_suggestions(profile))

    # Sort by confidence descending, deduplicate by slug (keep highest confidence)
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
        # Prompt is intentionally minimal — the heuristics handle the main cases.
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
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
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
```

**Step 4: Update `checks/__init__.py`**

Add to exports:
```python
from dqt.checks.suggest import ColumnProfile, SuggestedCheck, suggest_checks_for_column
```

**Step 5: Run tests, verify pass**
```
uv run pytest packages/dqt/tests/checks/test_suggest.py -v
```
Expected: all tests pass.

**Step 6: Commit**
```bash
git add packages/dqt/src/dqt/checks/suggest.py packages/dqt/src/dqt/checks/__init__.py packages/dqt/tests/checks/test_suggest.py
git commit -m "feat(m1): dqt.checks.suggest heuristic check suggestion engine"
```

---

### Task 2: `dqt.metrics.Metric` and `MetricRegistry`

**Files:**
- Modify: `packages/dqt/src/dqt/metrics/__init__.py`
- Create: `packages/dqt/src/dqt/metrics/models.py`
- Create: `packages/dqt/src/dqt/metrics/registry.py`
- Create: `packages/dqt/tests/metrics/test_registry.py`

**Step 1: Write failing tests**

```python
# packages/dqt/tests/metrics/test_registry.py
import pytest
from unittest.mock import MagicMock, patch
from dqt.metrics import Metric, MetricRegistry


def _make_registry(metrics: list[Metric]) -> MetricRegistry:
    r = MetricRegistry.__new__(MetricRegistry)
    r._metrics = {m.fqn: m for m in metrics}
    return r


def test_metric_has_required_fields():
    m = Metric(
        fqn="gigler.public.gigler_transactions.null_fraction",
        display_name="Null fraction — gigler_transactions",
        kind="ratio",
        dataset="gigler_transactions",
        description="Fraction of NULL values.",
        owners=[],
        tags=[],
    )
    assert m.fqn
    assert m.display_name
    assert m.kind in ("ratio", "count", "sum", "model")


def test_registry_get():
    m = Metric(fqn="a.b.c.d", display_name="D", kind="count", dataset="ds",
               description="", owners=[], tags=[])
    reg = _make_registry([m])
    assert reg.get("a.b.c.d") is m


def test_registry_get_missing_returns_none():
    reg = _make_registry([])
    assert reg.get("nonexistent") is None


def test_registry_search_by_display_name():
    m1 = Metric(fqn="a", display_name="Revenue total", kind="sum", dataset="orders",
                description="", owners=[], tags=[])
    m2 = Metric(fqn="b", display_name="Churn rate", kind="ratio", dataset="users",
                description="", owners=[], tags=[])
    reg = _make_registry([m1, m2])
    results = reg.search("revenue")
    assert any(r.fqn == "a" for r in results)
    assert not any(r.fqn == "b" for r in results)


def test_registry_search_case_insensitive():
    m = Metric(fqn="a", display_name="Revenue Total", kind="sum", dataset="ds",
               description="", owners=[], tags=[])
    reg = _make_registry([m])
    assert reg.search("REVENUE")


def test_registry_list_all():
    metrics = [
        Metric(fqn=f"m{i}", display_name=f"M{i}", kind="count", dataset="ds",
               description="", owners=[], tags=[])
        for i in range(5)
    ]
    reg = _make_registry(metrics)
    assert len(reg.list()) == 5


def test_registry_list_filter_by_tag():
    m1 = Metric(fqn="a", display_name="A", kind="count", dataset="ds",
                description="", owners=[], tags=["finance"])
    m2 = Metric(fqn="b", display_name="B", kind="count", dataset="ds",
                description="", owners=[], tags=["marketing"])
    reg = _make_registry([m1, m2])
    assert [r.fqn for r in reg.list(tags=["finance"])] == ["a"]


def test_registry_list_filter_by_owner():
    m1 = Metric(fqn="a", display_name="A", kind="count", dataset="ds",
                description="", owners=["alice"], tags=[])
    m2 = Metric(fqn="b", display_name="B", kind="count", dataset="ds",
                description="", owners=["bob"], tags=[])
    reg = _make_registry([m1, m2])
    assert [r.fqn for r in reg.list(owner="alice")] == ["a"]
```

**Step 2: Verify tests fail**
```
uv run pytest packages/dqt/tests/metrics/test_registry.py -v
```
Expected: ImportError on `dqt.metrics`.

**Step 3: Implement `models.py`**

```python
# packages/dqt/src/dqt/metrics/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

MetricKind = Literal["ratio", "count", "sum", "model"]


@dataclass
class Metric:
    fqn: str                    # fully-qualified name: source.schema.table.metric_name
    display_name: str
    kind: MetricKind
    dataset: str                # dataset id this metric is derived from
    description: str
    owners: list[str]
    tags: list[str]
    unit: str = ""
    warn_threshold: float | None = None
    fail_threshold: float | None = None
    # Populated at runtime from results store
    current_value: float | None = None
    current_verdict: str | None = None
    last_run: str | None = None
```

**Step 4: Implement `registry.py`**

```python
# packages/dqt/src/dqt/metrics/registry.py
from __future__ import annotations
from dqt.metrics.models import Metric

try:
    from rapidfuzz import fuzz as _fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


class MetricRegistry:
    """In-memory registry of Metric definitions. Thread-safe reads; not concurrent writes."""

    def __init__(self, metrics: list[Metric] | None = None) -> None:
        self._metrics: dict[str, Metric] = {}
        for m in (metrics or []):
            self._metrics[m.fqn] = m

    def get(self, fqn: str) -> Metric | None:
        return self._metrics.get(fqn)

    def search(self, query: str, limit: int = 20) -> list[Metric]:
        q = query.lower()
        if _HAS_RAPIDFUZZ:
            scored = [
                (m, _fuzz.WRatio(q, m.display_name.lower()))
                for m in self._metrics.values()
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [m for m, score in scored[:limit] if score > 40]
        # Fallback: substring match
        return [
            m for m in self._metrics.values()
            if q in m.display_name.lower() or q in m.fqn.lower()
        ][:limit]

    def list(
        self,
        *,
        tags: list[str] | None = None,
        owner: str | None = None,
        status: str | None = None,
    ) -> list[Metric]:
        results = list(self._metrics.values())
        if tags:
            tag_set = set(tags)
            results = [m for m in results if tag_set.intersection(m.tags)]
        if owner:
            results = [m for m in results if owner in m.owners]
        return results

    def reload(self, metrics: list[Metric]) -> None:
        self._metrics = {m.fqn: m for m in metrics}
```

**Step 5: Update `metrics/__init__.py`**

```python
from dqt.metrics.models import Metric, MetricKind
from dqt.metrics.registry import MetricRegistry

__all__ = ["Metric", "MetricKind", "MetricRegistry"]
```

**Step 6: Run tests, verify pass**
```
uv run pytest packages/dqt/tests/metrics/test_registry.py -v
```
Expected: all tests pass.

**Step 7: Run full suite, confirm no regressions**
```
uv run pytest packages/dqt/tests/ -x -q --tb=short
```
Expected: same or better than baseline (110 pass, 1 pre-existing fail).

**Step 8: Commit**
```bash
git add packages/dqt/src/dqt/metrics/ packages/dqt/tests/metrics/
git commit -m "feat(m1): Metric dataclass and MetricRegistry"
```

---

### Task 3: Suggest API endpoint

**Files:**
- Create: `apps/server/src/dqt_server/api/v1/suggest.py`
- Modify: `apps/server/src/dqt_server/main.py`

**Step 1: Write failing test**

```python
# apps/server/tests/test_suggest_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from dqt_server.main import app

@pytest.mark.asyncio
async def test_suggest_endpoint_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/datasets/gigler_transactions/columns/price_id/suggest"
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "detector_slug" in data[0]
        assert "rationale" in data[0]
        assert "confidence" in data[0]

@pytest.mark.asyncio
async def test_suggest_unknown_dataset_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/datasets/nonexistent_table/columns/id/suggest"
        )
    assert resp.status_code == 404
```

**Step 2: Implement `suggest.py` router**

```python
# apps/server/src/dqt_server/api/v1/suggest.py
"""Column-level check suggestion endpoint."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.models.gigler import Dataset
from dqt_server.gigler_service import gigler_service
from dqt.checks.suggest import ColumnProfile, SuggestedCheck, suggest_checks_for_column

router = APIRouter(prefix="/api/v1", tags=["suggest"])


def _build_profile(dataset_id: str, column: str, profile_data: dict) -> ColumnProfile:
    name = column
    data_type = profile_data.get("data_type", "text")
    null_fraction = profile_data.get("null_fraction", 0.0)
    distinct_count = profile_data.get("distinct_count", 0)
    sample_values = profile_data.get("sample_values", [])
    min_value = profile_data.get("min_value")
    max_value = profile_data.get("max_value")

    name_lower = name.lower()
    is_likely_pk = (
        name_lower in ("id", f"{dataset_id}_id", "pk")
        or name_lower.endswith("_id")
        and distinct_count > 1000
        and null_fraction == 0.0
    )
    is_likely_fk = name_lower.endswith("_id") and not is_likely_pk
    is_likely_enum = distinct_count > 0 and distinct_count < 50
    is_likely_email = "email" in name_lower or any("@" in v for v in sample_values[:5])
    is_likely_timestamp = "timestamp" in data_type.lower() or "date" in data_type.lower() or any(k in name_lower for k in ("_at", "_date", "_time", "timestamp", "created", "updated"))
    is_likely_currency = any(k in name_lower for k in ("amount", "price", "revenue", "cost", "fee", "total"))
    is_likely_country = name_lower in ("country", "country_code", "country_iso") or (distinct_count > 0 and distinct_count < 300 and all(len(v) == 2 for v in sample_values[:5] if v))

    return ColumnProfile(
        name=name,
        data_type=data_type,
        null_fraction=null_fraction,
        distinct_count=distinct_count,
        sample_values=[str(v) for v in sample_values[:10]],
        min_value=min_value,
        max_value=max_value,
        is_likely_pk=is_likely_pk,
        is_likely_fk=is_likely_fk,
        is_likely_enum=is_likely_enum,
        is_likely_email=is_likely_email,
        is_likely_timestamp=is_likely_timestamp,
        is_likely_currency=is_likely_currency,
        is_likely_country=is_likely_country,
        sample_size_used=profile_data.get("sample_size", 0),
    )


@router.get("/datasets/{dataset_id}/columns/{column}/suggest")
async def suggest_checks(
    dataset_id: str,
    column: str,
    use_llm: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return ranked check suggestions for a column."""
    d = await db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{dataset_id}' not found")

    loop = asyncio.get_event_loop()
    try:
        profile_data = await loop.run_in_executor(
            None, gigler_service._profile_column_sync, dataset_id, column
        )
    except Exception:
        profile_data = {}

    profile = _build_profile(dataset_id, column, profile_data)
    suggestions = suggest_checks_for_column(profile, use_llm=use_llm)

    return [
        {
            "detector_slug": s.detector_slug,
            "params": s.params,
            "rationale": s.rationale,
            "confidence": round(s.confidence, 3),
        }
        for s in suggestions
    ]
```

**Step 3: Register router in `main.py`**

Add after existing router includes:
```python
from dqt_server.api.v1.suggest import router as suggest_router
app.include_router(suggest_router)
```

**Step 4: Run tests**
```
uv run pytest apps/server/tests/test_suggest_api.py -v
```
Expected: both tests pass.

**Step 5: Commit**
```bash
git add apps/server/src/dqt_server/api/v1/suggest.py apps/server/src/dqt_server/main.py apps/server/tests/test_suggest_api.py
git commit -m "feat(m1): GET /api/v1/datasets/{id}/columns/{column}/suggest endpoint"
```

---

### Task 4: Column profile page — AI suggestions section

**Files:**
- Modify: `apps/web/src/app/(app)/datasets/[id]/[column]/page.tsx`
- Create: `apps/web/src/components/checks/suggest-panel.tsx`

Note: Check what currently exists in the column profile page before modifying.

**Step 1: Create client-side `SuggestPanel` component**

```tsx
// apps/web/src/components/checks/suggest-panel.tsx
"use client"

import { useState, useEffect } from "react"

interface Suggestion {
  detector_slug: string
  params: Record<string, unknown>
  rationale: string
  confidence: number
}

export function SuggestPanel({ datasetId, column }: { datasetId: string; column: string }) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [accepted, setAccepted] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetch(`/api/v1/datasets/${datasetId}/columns/${encodeURIComponent(column)}/suggest`)
      .then((r) => r.ok ? r.json() : [])
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
      .finally(() => setLoading(false))
  }, [datasetId, column])

  if (loading) {
    return (
      <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>
        Loading suggestions...
      </div>
    )
  }

  if (suggestions.length === 0) {
    return (
      <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>
        No suggestions available.
      </div>
    )
  }

  return (
    <div className="divide-y divide-line">
      {suggestions.map((s) => {
        const isAccepted = accepted.has(s.detector_slug)
        return (
          <div key={s.detector_slug} className="px-4 py-3 flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>
                  {s.detector_slug}
                </span>
                <span
                  className="t-micro px-1 py-0.5"
                  style={{
                    background: s.confidence >= 0.8 ? "rgba(127,179,148,0.12)" : "rgba(217,181,102,0.12)",
                    color: s.confidence >= 0.8 ? "var(--pass)" : "var(--warn)",
                    fontFamily: "var(--font-jetbrains-mono)",
                  }}
                >
                  {(s.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="t-micro" style={{ color: "var(--fg-2)" }}>{s.rationale}</p>
            </div>
            <button
              onClick={() => setAccepted((prev) => new Set([...prev, s.detector_slug]))}
              disabled={isAccepted}
              className="t-micro px-2 py-1 border transition-colors flex-shrink-0"
              style={{
                borderColor: isAccepted ? "var(--pass)" : "var(--line-3)",
                color: isAccepted ? "var(--pass)" : "var(--fg-2)",
                background: "transparent",
                cursor: isAccepted ? "default" : "pointer",
              }}
            >
              {isAccepted ? "accepted" : "accept"}
            </button>
          </div>
        )
      })}
    </div>
  )
}
```

**Step 2: Add suggestions section to column profile page**

Read the current `apps/web/src/app/(app)/datasets/[id]/[column]/page.tsx` first, then add the `SuggestPanel` section near the bottom, after the existing content. Import `SuggestPanel` as a dynamic import with `{ ssr: false }` to avoid server-side fetch conflicts.

```tsx
import dynamic from "next/dynamic"
const SuggestPanel = dynamic(
  () => import("@/components/checks/suggest-panel").then(m => m.SuggestPanel),
  { ssr: false, loading: () => <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>Loading...</div> }
)

// Add this section at the bottom of the page component, before the closing </div>:
<div className="mt-6 border border-line" style={{ background: "var(--bg-1)" }}>
  <div className="px-4 py-3 border-b border-line t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
    AI check suggestions
  </div>
  <SuggestPanel datasetId={dataset_id} column={column} />
</div>
```

**Step 3: Verify build passes**
```
pnpm --filter web build
```
Fix any TypeScript errors before committing.

**Step 4: Commit**
```bash
git add apps/web/src/components/checks/suggest-panel.tsx apps/web/src/app/(app)/datasets/
git commit -m "feat(m1): AI check suggestions panel in column profile page"
```

---

### Task 5: Archive existing metrics page

**Files:**
- Modify: `apps/web/src/app/(app)/metrics/page.tsx`

Replace the entire metrics page content with a placeholder. The metric insight page arrives in M2.

```tsx
// apps/web/src/app/(app)/metrics/page.tsx
export default function MetricsPage() {
  return (
    <div className="p-6">
      <h1 className="t-h1 mb-2" style={{ color: "var(--fg-0)" }}>Metrics</h1>
      <p className="t-small mb-6" style={{ color: "var(--fg-2)" }}>
        The metric insight page is being rebuilt for v1.1. Full two-channel reconciliation,
        narrative explanations, and the Why Layer arrive with the next release.
      </p>
      <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
        <p className="t-small font-mono mb-2" style={{ color: "var(--fg-3)" }}>v1.1.0 — coming next</p>
        <p className="t-body" style={{ color: "var(--fg-1)" }}>
          Metric insight page with two-channel reconciliation
        </p>
        <p className="t-small mt-2" style={{ color: "var(--fg-3)" }}>
          In the meantime, explore metrics via the Datasets and Causality pages.
        </p>
      </div>
    </div>
  )
}
```

**Verify build:**
```
pnpm --filter web build
```

**Commit:**
```bash
git add apps/web/src/app/(app)/metrics/page.tsx
git commit -m "feat(m1): archive mock metrics page, placeholder for v1.1 metric insight"
```

---

### Task 6: M1 eval — verify ≥70% suggestion acceptance rate

**Files:**
- Create: `packages/dqt/tests/checks/test_suggest_eval.py`

```python
# packages/dqt/tests/checks/test_suggest_eval.py
"""Eval gate: ≥70% of labeled fixtures should produce accepted suggestions.
Each fixture has a profile and a set of detector_slugs we'd accept.
A fixture passes if at least one expected slug appears in the suggestions.
"""
import pytest
from dqt.checks.suggest import ColumnProfile, suggest_checks_for_column


FIXTURES = [
    # (profile_kwargs, accepted_slugs, description)
    ({"name": "id", "data_type": "integer", "null_fraction": 0.0, "distinct_count": 100000, "is_likely_pk": True, "sample_values": []}, {"null_fraction", "uniqueness"}, "integer PK"),
    ({"name": "user_id", "data_type": "integer", "null_fraction": 0.02, "distinct_count": 5000, "is_likely_fk": True, "sample_values": []}, {"referential_integrity"}, "FK column"),
    ({"name": "email", "data_type": "text", "null_fraction": 0.0, "distinct_count": 50000, "is_likely_email": True, "sample_values": ["alice@example.com"]}, {"regex_match"}, "email column"),
    ({"name": "status", "data_type": "text", "null_fraction": 0.01, "distinct_count": 4, "is_likely_enum": True, "sample_values": ["active", "inactive", "pending", "deleted"]}, {"set_membership"}, "enum column"),
    ({"name": "country_code", "data_type": "text", "null_fraction": 0.0, "distinct_count": 50, "is_likely_country": True, "sample_values": ["US", "GB", "DE"]}, {"set_membership"}, "country code"),
    ({"name": "created_at", "data_type": "timestamp", "null_fraction": 0.0, "distinct_count": 90000, "is_likely_timestamp": True, "sample_values": []}, {"freshness_seconds_behind"}, "timestamp"),
    ({"name": "amount", "data_type": "float", "null_fraction": 0.0, "distinct_count": 10000, "is_likely_currency": True, "min_value": -5.0, "max_value": 5000.0, "sample_values": []}, {"value_in_range"}, "currency with negatives"),
    ({"name": "price", "data_type": "float", "null_fraction": 0.0, "distinct_count": 1000, "is_likely_currency": True, "min_value": 0.0, "max_value": 999.0, "sample_values": []}, {"value_in_range"}, "price column no negatives"),
    ({"name": "revenue", "data_type": "decimal", "null_fraction": 0.0, "distinct_count": 50000, "is_likely_currency": False, "min_value": 0.0, "max_value": 1e6, "sample_values": []}, {"mad_outlier_fraction"}, "heavy-tailed numeric"),
    ({"name": "score", "data_type": "float", "null_fraction": 0.05, "distinct_count": 10000, "is_likely_currency": False, "min_value": 0.0, "max_value": 1.0, "sample_values": []}, {"mad_outlier_fraction", "null_fraction"}, "score column with nulls"),
    # 10 more edge cases
    ({"name": "transaction_id", "data_type": "varchar", "null_fraction": 0.0, "distinct_count": 1000000, "is_likely_pk": True, "sample_values": []}, {"uniqueness"}, "varchar PK"),
    ({"name": "product_id", "data_type": "bigint", "null_fraction": 0.0, "distinct_count": 50000, "is_likely_fk": True, "sample_values": []}, {"referential_integrity"}, "bigint FK"),
    ({"name": "user_email", "data_type": "varchar", "null_fraction": 0.0, "distinct_count": 8000, "is_likely_email": True, "sample_values": ["b@c.net"]}, {"regex_match"}, "user_email column"),
    ({"name": "payment_status", "data_type": "varchar", "null_fraction": 0.0, "distinct_count": 3, "is_likely_enum": True, "sample_values": ["paid", "unpaid", "refunded"]}, {"set_membership"}, "payment status enum"),
    ({"name": "country", "data_type": "char(2)", "null_fraction": 0.0, "distinct_count": 40, "is_likely_country": True, "sample_values": ["US", "CA", "MX"]}, {"set_membership"}, "country char2"),
    ({"name": "updated_at", "data_type": "datetime", "null_fraction": 0.1, "distinct_count": 80000, "is_likely_timestamp": True, "sample_values": []}, {"freshness_seconds_behind"}, "nullable updated_at"),
    ({"name": "order_total", "data_type": "numeric", "null_fraction": 0.0, "distinct_count": 20000, "is_likely_currency": True, "min_value": -100.0, "max_value": 10000.0, "sample_values": []}, {"value_in_range"}, "order_total with refunds"),
    ({"name": "session_duration", "data_type": "integer", "null_fraction": 0.15, "distinct_count": 3000, "is_likely_currency": False, "min_value": 0, "max_value": 7200, "sample_values": []}, {"mad_outlier_fraction", "null_fraction"}, "session duration"),
    ({"name": "category", "data_type": "text", "null_fraction": 0.02, "distinct_count": 12, "is_likely_enum": True, "sample_values": ["electronics", "books", "clothing"]}, {"set_membership"}, "category enum"),
    ({"name": "discount_pct", "data_type": "float", "null_fraction": 0.3, "distinct_count": 50, "is_likely_currency": False, "min_value": 0.0, "max_value": 1.0, "sample_values": []}, {"null_fraction", "value_in_range"}, "discount percentage"),
    # 10 more
    ({"name": "vendor_id", "data_type": "integer", "null_fraction": 0.0, "distinct_count": 500, "is_likely_fk": True, "sample_values": []}, {"referential_integrity"}, "vendor FK"),
    ({"name": "signup_email", "data_type": "text", "null_fraction": 0.0, "distinct_count": 100000, "is_likely_email": True, "sample_values": ["x@y.com"]}, {"regex_match"}, "signup email"),
    ({"name": "region_code", "data_type": "varchar(2)", "null_fraction": 0.0, "distinct_count": 25, "is_likely_country": True, "sample_values": ["EU", "US", "APAC"]}, {"set_membership"}, "region code"),
    ({"name": "plan_type", "data_type": "varchar", "null_fraction": 0.0, "distinct_count": 5, "is_likely_enum": True, "sample_values": ["free", "starter", "pro", "enterprise", "trial"]}, {"set_membership"}, "plan type enum"),
    ({"name": "invoice_date", "data_type": "date", "null_fraction": 0.0, "distinct_count": 365, "is_likely_timestamp": True, "sample_values": []}, {"freshness_seconds_behind"}, "invoice date"),
    ({"name": "mrr", "data_type": "float", "null_fraction": 0.0, "distinct_count": 5000, "is_likely_currency": True, "min_value": 0.0, "max_value": 50000.0, "sample_values": []}, {"value_in_range"}, "MRR metric"),
    ({"name": "churn_flag", "data_type": "boolean", "null_fraction": 0.0, "distinct_count": 2, "is_likely_enum": True, "sample_values": ["true", "false"]}, {"set_membership"}, "boolean flag as enum"),
    ({"name": "lat", "data_type": "float", "null_fraction": 0.05, "distinct_count": 100000, "min_value": -90.0, "max_value": 90.0, "sample_values": []}, {"value_in_range", "mad_outlier_fraction"}, "latitude column"),
    ({"name": "record_id", "data_type": "uuid", "null_fraction": 0.0, "distinct_count": 500000, "is_likely_pk": True, "sample_values": []}, {"null_fraction", "uniqueness"}, "UUID PK"),
    ({"name": "tax_rate", "data_type": "float", "null_fraction": 0.0, "distinct_count": 20, "is_likely_enum": True, "sample_values": ["0.0", "0.1", "0.15", "0.2"]}, {"set_membership"}, "tax rate enum"),
]


def _defaults() -> dict:
    return dict(
        null_fraction=0.0, distinct_count=100, sample_values=[],
        min_value=None, max_value=None,
        is_likely_pk=False, is_likely_fk=False, is_likely_enum=False,
        is_likely_email=False, is_likely_timestamp=False,
        is_likely_currency=False, is_likely_country=False,
        data_type="text",
    )


def test_suggestion_eval_gate():
    passed = 0
    failed_descriptions = []
    for kwargs, expected_slugs, description in FIXTURES:
        profile = ColumnProfile(**{**_defaults(), **kwargs})
        suggestions = suggest_checks_for_column(profile, use_llm=False)
        got_slugs = {s.detector_slug for s in suggestions}
        if got_slugs.intersection(expected_slugs):
            passed += 1
        else:
            failed_descriptions.append(
                f"FAIL: {description} — expected one of {expected_slugs}, got {got_slugs}"
            )
    
    total = len(FIXTURES)
    rate = passed / total
    print(f"\nSuggestion eval: {passed}/{total} = {rate:.1%}")
    for f in failed_descriptions:
        print(f)
    
    assert rate >= 0.70, f"Suggestion accept rate {rate:.1%} below 70% gate"
```

**Run eval:**
```
uv run pytest packages/dqt/tests/checks/test_suggest_eval.py -v -s
```
Expected: ≥70% pass rate (21 of 30+ fixtures).

**Commit if gate passes:**
```bash
git add packages/dqt/tests/checks/test_suggest_eval.py
git commit -m "test(m1): suggestion eval gate — ≥70% acceptance rate on labeled fixtures"
```

---

### Task 7: Final gate check

**Step 1: Run full library test suite**
```
uv run pytest packages/dqt/tests/ -x -q --tb=short
```
Expected: same or better than baseline (110 pass, 1 pre-existing psycopg2 fail).

**Step 2: Run build**
```
pnpm --filter web build
```
Expected: no errors, no warnings about new components.

**Step 3: Confirm 64 detector docs**
```
uv run pytest packages/dqt/tests/ -k "docs" -v
```
Expected: 128/128 pass (if this test exists).

**Step 4: Write CHANGELOG entry**

Add to `CHANGELOG.md` under a new `## v1.1.0-RC` section:
```markdown
## v1.1.0-RC

### Added
- `dqt.checks.suggest` — heuristic + LLM-augmented check suggestion engine (`ColumnProfile`, `SuggestedCheck`, `suggest_checks_for_column`)
- `dqt.metrics.Metric` and `dqt.metrics.MetricRegistry` — foundation data types for M2 reconciliation engine
- `GET /api/v1/datasets/{dataset_id}/columns/{column}/suggest` — ranked check suggestions for any column
- AI suggestions panel in the column profile view (web UI)

### Changed
- Metrics page archived (placeholder); full metric insight page arrives in v1.1.0

### Notes
- All 64 detector docs unchanged (v1.x contract holds)
- v0.4.3 CI eval suite: zero regressions
```

**Step 5: Final commit**
```bash
git add CHANGELOG.md
git commit -m "chore(m1): CHANGELOG entry for v1.1.0-RC milestone 1"
```

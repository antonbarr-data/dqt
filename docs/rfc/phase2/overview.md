# Phase 2 — The Why Layer for BI: Architecture Overview

> v1.3.0 target. Built on top of stable v1.0 (28 releases, zero regressions).

## Positioning

dqt sits beside your BI stack and answers the question it can't: **why did this metric move?**

Every metric movement is reconciled across two channels:
- **Channel A — Data integrity:** failed checks, schema changes, freshness slips, null rate spikes upstream
- **Channel B — Business drivers:** causal evidence, mix shifts, external signals

## Milestone sequence

```
M1 → M2 → M3 → M4 → M5
               ↑
        M5 lineage work starts in parallel with M3/M4
```

- **M1 (v1.1.0-RC):** Foundation — check suggestions, Metric/MetricRegistry, datasets API augments
- **M2 (v1.2.0-RC):** Core — two-channel reconciliation engine, narrative pipeline, metric insight page
- **M3:** Today feed, Ask bar, search
- **M4:** Subscriptions, digests, Slack/email delivery
- **M5 (v1.3.0):** Lineage explorer, reviewer queue, hardening, release

## Architecture decisions

### Option A: Extend existing apps (confirmed by author)

The brief describes a standalone `dqt metrics serve` SPA on port 8090 with a Vite frontend. The author has chosen to extend the existing `apps/server` (FastAPI) + `apps/web` (Next.js) instead. Rationale: single deployment, shared auth, existing design system, no split codebase.

Implications:
- All new frontend pages go in `apps/web/src/app/(app)/`
- All new API endpoints go in `apps/server/src/dqt_server/api/v1/`
- Brand tokens are already in `apps/web/src/app/globals.css` — no changes
- `dqt metrics serve` CLI is deferred; the server itself serves everything
- The Vite SPA described in the brief is NOT being built

### Page replaced in M1

`apps/web/src/app/(app)/metrics/page.tsx` — the existing mock metrics dashboard — is archived in M1 (replaced with a placeholder pointing to v1.1). M2 replaces it with the real metric insight page.

### New pages added per milestone

- M1: No new pages. Augment existing `/datasets/[id]/[column]` column profile view with AI suggestions + check picker.
- M2: Replace `/metrics` with full metric insight page (`/metrics/[fqn]`)
- M3: Add `/` Today feed homepage, `/ask` page, `/search` page
- M4: Add `/subscriptions` page
- M5: Add `/metrics/[fqn]/lineage`, `/causal/review`

## Key data types (Phase 2 contracts)

```python
# M1
@dataclass
class ColumnProfile: ...         # packages/dqt/src/dqt/checks/suggest.py
class SuggestedCheck: ...        # packages/dqt/src/dqt/checks/suggest.py
class Metric: ...                # packages/dqt/src/dqt/metrics/models.py
class MetricRegistry: ...        # packages/dqt/src/dqt/metrics/registry.py

# M2
@dataclass
class DataIssue: ...             # packages/dqt/src/dqt/insights/channel_a.py
class RankedCause: ...           # packages/dqt/src/dqt/insights/channel_b.py
class MixShiftReport: ...        # packages/dqt/src/dqt/insights/mixshift.py
class MovementExplanation: ...   # packages/dqt/src/dqt/insights/models.py
```

## What does NOT change in Phase 2

- 64 documented detectors (public v1.x contract)
- 6 production warehouse adapters (public v1.x contract)
- Algorithm defaults (v0.9.3 calibration tables are public contracts)
- Existing `dqt dashboard` (serves data engineers; new product serves analysts)
- v1.0 module structure (stability era)

## Acceptance gates (every milestone)

1. All milestone acceptance criteria pass
2. v0.4.3 CI eval suite passes
3. 64 detector docs still ship (128/128 completeness tests green)
4. No new detector defaults changed
5. Visual QA: every new/changed page reviewed
6. New public symbols documented in `STABILITY.md`
7. New API endpoints documented in `docs/api/insights.md`
8. CHANGELOG.md entry written
9. Bundle size: <1MB total, <500KB initial JS payload

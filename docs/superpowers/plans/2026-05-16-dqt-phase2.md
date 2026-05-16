# dqt Phase 2 — The Why Layer for BI

**Audience:** Claude Code (with Superpowers — planning, subagents, parallel execution, TDD)
**Target release:** v1.3.0
**Status of v1.0:** stable, 28 releases shipped, zero regressions on the v0.4.3 CI eval suite, 64 documented detectors, 6 production warehouse adapters
**This document:** the complete brief for Phase 2. Read it end to end before writing any code or invoking any subagent.

---

## 0. How to work this brief

### Operating principles for Claude Code

- **Plan before you build.** Each milestone gets a planning pass — read the milestone, decompose into subagent tracks, identify dependencies, write the plan to `docs/rfc/phase2/milestone-N.md`, then start work.
- **TDD throughout.** Every public API gets a test before the implementation. Every UI page gets a Playwright E2E before the handlers. The v0.4.3 CI eval suite must pass on every PR.
- **Use subagents in parallel.** Each milestone names its subagent tracks. Fan out aggressively; merge through PRs against a milestone branch.
- **Evaluation subagents are non-negotiable.** Quality of suggested checks, narrative prose, and ask-resolution all need labeled-fixture review before the milestone passes. These are explicitly subagent tracks, not afterthoughts.
- **Single-purpose discipline.** No new detectors. No new adapters. No algorithm default changes. No dashboard regressions. The v1.0 stability contract holds.
- **No scope creep.** If something isn't in this brief, it's v1.4+. Document the deferral, move on.
- **Stop after first fix-and-verify on visual QA.** Don't loop chasing pixel-perfect; user-visible defects only.

### Acceptance gates between every milestone

A milestone is "done" only when all of these pass:

1. All acceptance criteria in the milestone section
2. v0.4.3 CI eval suite passes (no regressions across 28+ historical fixes)
3. 64 detector docs still ship (`tests/docs/test_docs_completeness.py` green, 128/128)
4. No new detector defaults have changed (v1.0 calibration tables are public contracts)
5. Visual QA subagent has reviewed every new/changed page, found no user-visible defects
6. New public API symbols added to `STABILITY.md`
7. API contracts documented in `docs/api/insights.md` (extended each milestone)
8. CHANGELOG.md entry for the milestone
9. Bundle size budget met (<1MB total, <500KB initial JS payload)

The planning agent verifies these gates before releasing the next milestone's subagents.

---

## 1. Product framing

**Single-sentence positioning:**

> dqt sits beside your BI stack and answers the question it can't: **why did this metric move?**

Tableau, Looker, Sigma, Mode, and Hex tell you *what* and *how much*. Monte Carlo, Anomalo, and Bigeye tell you *what failed*. dqt tells you *why*, every day, for every metric you care about — proactively in Slack and email, on demand when you ask, and continuously refreshed on a feed you can scan in two minutes.

**The pain point being solved:** BI teams get pinged constantly with "why is X up/down/weird this week?" Each question requires checking data quality, pulling related metrics, eyeballing correlations, asking data engineering if anything changed, asking product if anything launched, looking at competitor signals, writing it up. It takes days. dqt makes that finished answer the default state of every metric, not something an analyst manually produces.

**The differentiating capability:** every "why" answer reconciles two channels:

- **Channel A — Data integrity:** is this movement a data issue? (failed checks, schema changes, freshness slips, null rate spikes upstream)
- **Channel B — Business drivers:** is this a real shift? (causal evidence across the metric catalog, mix shifts, external signals)

Every narrative says explicitly which channel dominates and by what magnitude. The audience for the reconciliation is both business users ("is it real before I tell the CFO?") and data engineers ("is there a bug I need to fix today?"). No other tool produces this reconciliation today.

**The product surface:** insights, not infrastructure. Most users open dqt once a day, scan the Today feed for two minutes, click into one or two items, forward one Slack message, and close it. Power users dig deeper through the metric insight page, the ask bar, the lineage explorer. Data engineers use the reviewer queue and dataset browser. All four user types share the same engine.

---

## 2. The four product surfaces

### 2.1 Today feed (the homepage)

Push-style entry point. Default landing page.

A chronological feed of the most important metric movements in the last 24 hours (configurable to weekly view). Each item:

- Metric name and current change (revenue down 18%)
- One-paragraph reconciled narrative — what's data, what's real, what changed
- Three evidence chips with sparklines (e.g. avg price ↓4%, supply ↓12%, null fraction ↑4.2%)
- "Dig deeper" link → metric insight page
- "Share to Slack" and "Mark reviewed" actions

Importance ranking combines: magnitude of move, statistical significance, executive-tier tag on metric, novelty (not surfaced recently), team engagement signal (has anyone clicked into related items).

### 2.2 Ask bar (the pull entry point)

Available as Cmd-K modal from any page and dedicated `/ask` page. Handles natural language:

- "Why is revenue down this week?"
- "What's driving the spike in cancellations?"
- "Is the drop in signups a data issue?"
- "Compare login count and revenue over the last 30 days"
- "Show me which metrics moved significantly yesterday"

Resolution flow: parse → identify metric(s) → identify window → identify intent (why/compare/list) → run engine → render. When the question is ambiguous, ask back rather than guess.

### 2.3 Metric insight page

Deep dive for a single metric. Reachable from feed, search, ask, and Slack deep links.

Layout, top to bottom:

1. **Header** — metric display name, fqn in mono, current verdict chip, last-run timestamp, owner pill, pin button, "Subscribe" button
2. **Current insight narrative** — auto-generated prose answering "why is this metric where it is right now," refreshed nightly or on demand
3. **Reconciliation bar** — visual split showing estimated Channel A vs Channel B contribution
4. **Time-window picker** — 7d, 30d, MTD, QTD, since last release, custom range — changes narrative + chart
5. **Evidence table** — every signal the engine considered, with how it scored (expandable rows)
6. **Time series chart** — values with verdict markers overlaid
7. **Lineage strip** — horizontal mini-graph, 3 up + 3 down, "see full lineage" link
8. **Recent incidents** — last 5, click-through to incident-focused explanation
9. **Active checks** — list with thresholds and 30-run sparklines; "+ add check" → milestone 1's picker
10. **Audit drawer** — click any sentence in the narrative → see the specific evidence rows that produced it

### 2.4 Subscriptions and digests

The proactive surface. Most subscribed users live in their Slack/email, never opening the UI.

**Subscription model:** user + metrics + cadence (daily/weekly/on-significant-move) + delivery channel (Slack/email/both) + per-metric significance thresholds.

**Digest formats:**

- **Reactive ping** (on threshold cross): "Three metrics moved meaningfully overnight. *Revenue*: up 4% on stronger weekend supply (real shift, no data issues). *New signups*: down 11% — likely a data issue from the auth release; ~$30k revenue impact at risk if not fixed today. *Churn rate*: unchanged from baseline."
- **Daily morning digest** (configurable cron): same shape, runs daily
- **Weekly business review** (Monday 8 AM default): expanded narrative with headline, real business shifts section, data integrity section, "requires attention" list, "now resolved" list

Slack delivery via Block Kit (existing `dqt.bot` extension). Email delivery via configurable SMTP.

---

## 3. The two-channel reconciliation engine

The heart of Phase 2. Every metric movement is explained through two parallel channels, reconciled into a single narrative.

### 3.1 Channel A — Data integrity

Inputs:
- Every check verdict upstream of the target metric within the movement window
- Schema change events upstream
- Freshness, volume, and completeness anomalies upstream
- Null rate, distinct count, and pattern check anomalies upstream

Per-issue scoring:
- Identify failed checks within the window
- Estimate magnitude of each issue's contribution to the observed movement (conservative heuristic with explicit ranges, e.g. "explains 2-6 percentage points")
- Rank by estimated contribution

Output: `list[DataIssue]` with magnitude estimates and links to underlying check verdicts.

### 3.2 Channel B — Business drivers

Inputs:
- All tracked metrics in the catalog as candidate causes
- Mix-shift decomposition over dimensions (geo, category, segment, channel) for aggregate metrics
- Product / engineering release events if integrated
- Marketing / commercial events if integrated
- External signals if configured (seasonality, holidays, competitor data)

Causal inference:
- Auto-route by candidate count: 1-3 → Granger pairwise; 4-15 → PCMCI+; 16+ → PCMCI+ with conditional independence pre-filtering
- Mix-shift decomposition runs first-class alongside causal — most marketplace "why" answers are mix shifts
- Rank candidates by causal evidence strength + p-value
- Produce ruled-out list (examined but rejected) with one-line "why ruled out" per item

Output: `list[RankedCause]`, `ruled_out: list[str]`, `mix_shift_decomposition: MixShiftReport`.

### 3.3 Reconciliation

Combines Channel A and Channel B into a single answer:

- Estimate contribution percentages with explicit ranges, not point estimates
- Determine `primary_channel: "data" | "business" | "mixed"`
- Generate prose narrative via LLM pipeline (section 4)

### 3.4 The MovementExplanation data type

```python
@dataclass
class MovementExplanation:
    metric: Metric
    window: tuple[datetime, datetime]
    observed_change: float                     # signed magnitude

    # Channel A
    data_issues: list[DataIssue]
    estimated_data_contribution: tuple[float, float]    # (low, high) range, 0.0-1.0

    # Channel B
    business_drivers: list[RankedCause]
    mix_shift: MixShiftReport | None
    ruled_out: list[RuledOutItem]
    estimated_business_contribution: tuple[float, float]

    # Reconciliation
    summary_paragraph: str
    primary_channel: Literal["data", "business", "mixed"]

    # Audit
    citations: dict[str, list[EvidenceRow]]    # sentence_id -> evidence rows
    computation_metadata: dict
```

The `citations` map is critical: it's what makes the narrative auditable. Every sentence in `summary_paragraph` gets a `sentence_id` and the `citations` map says exactly which evidence rows produced it.

---

## 4. The narrative generation pipeline

LLM-generated prose with structured guardrails. The whole value prop is "reads like an analyst wrote it," and template-driven prose hits a quality ceiling that doesn't meet the bar for executive-readable insights.

### 4.1 Pipeline flow

1. Two-channel engine produces structured `MovementExplanation` (causes, magnitudes, evidence rows)
2. Structured object rendered into a prompt with:
   - Metric definition and recent values
   - Ranked causes with evidence
   - Mix-shift decomposition if relevant
   - Channel reconciliation
   - Style guidance and required claim-citation format
3. LLM (via existing `dqt.wiki` Anthropic integration) produces prose
4. Post-processor validates every numeric claim traces back to a specific evidence row
5. Unsupported claims → regenerate
6. Final narrative cached alongside structured object

### 4.2 Guardrails

- **Every numeric claim must cite.** Post-processor parses the narrative for numbers, matches each to an evidence row, fails the narrative if any number is unsupported.
- **Style guide enforced via prompt.** Concise, analyst voice, no hedging when evidence is strong, explicit hedging when evidence is moderate, no superlatives without evidence.
- **Length cap.** Daily digest paragraphs ≤120 words. Insight page narratives ≤200 words. Weekly digest sections individually ≤80 words.
- **Sentence-level citation map populated.** Every output sentence has an ID; the `citations[sentence_id]` list names the evidence rows that produced it. Powers the audit drawer.

### 4.3 Fallback behavior

If the LLM is unavailable or post-processor rejects more than 3 times in a row:
- Fall back to template-driven prose
- Render a "fallback mode" banner on the surface
- Functionality degrades gracefully

### 4.4 Caching

Keyed on `(metric_fqn, window_hash, schema_version)`. TTL 6h business hours / 24h overnight. Invalidate on: new incident close within window, significant new data, threshold-cross event.

---

## 5. Milestone 1 — Foundation, datasets, and AI-suggested checks

**The infrastructure milestone.** Without this, there are no tracked metrics for the engine to explain.

### 5.1 Subagent decomposition

- `planner` — read all of phase 2.md, produce `docs/rfc/phase2/milestone-1.md`
- `backend-foundation` — `Metric`, `MetricRegistry`, migrations, `dqt metrics serve` CLI
- `backend-datasets-api` — dataset/column inventory endpoints
- `backend-suggester` — `dqt.checks.suggest` module
- `frontend-scaffold` — SPA setup, brand tokens, primitive components
- `frontend-datasets` — datasets page + check picker modal
- `eval-suggester` — labeled-fixture evaluation of suggestion quality (≥70% accept rate gate)

These six work in parallel after the planner produces the milestone plan.

### 5.2 Backend deliverables

**Archive existing metrics UI.** Delete source files. Remove routes. Return 410 Gone with "moved to v1.1" notice on old paths. Document in CHANGELOG.md under "Removed."

**`dqt.metrics.Metric`** — dataclass with identity (fqn, display_name), semantic layer (definition, citations, aliases, owners, tags), lineage (upstream, downstream, transformation_sql), quality (active_checks, open_incidents, recent_verdicts), and methods `series(lookback_days)` and (later) `causal_drivers(since)`.

**`dqt.metrics.MetricRegistry`** — orchestration over wiki + lineage + results store. Methods: `get(fqn)`, `search(query, limit)`, `list(tags, owner, status)`, `reload()`. Fuzzy match via RapidFuzz. In-memory cache, invalidate per-metric on wiki file change.

**`dqt migrate` CLI** — new subcommand. Schema migrations for `dqt_metric_pins`, `dqt_check_suggestions`, `dqt_causal_reviews_v2`, `dqt_ui_feedback`. Idempotent. `--dry-run` flag.

**Datasets API:**
- `GET /api/v1/datasets` — adapters → schemas → tables with row counts and column counts. Backed by adapter `list_schemas` and `list_tables`. Cached 5min.
- `GET /api/v1/datasets/{adapter}/{schema}/{table}/columns` — column list with type, recent null fraction, distinct count, sample values. Uses adapter `describe_columns` + `aggregate`.
- `GET /api/v1/columns/{adapter}/{schema}/{table}/{column}/checks` — all checks attached to this column
- `POST /api/v1/columns/.../checks` — attach a check
- `DELETE /api/v1/checks/{check_id}` — remove
- `PUT /api/v1/checks/{check_id}` — update params

**`dqt.checks.suggest` module:**

```python
@dataclass
class ColumnProfile:
    name: str
    data_type: str
    null_fraction: float
    distinct_count: int
    sample_values: list[str]
    min_value: Any | None
    max_value: Any | None
    is_likely_pk: bool          # uniqueness + non-null heuristic
    is_likely_fk: bool          # name pattern + cardinality
    is_likely_enum: bool        # distinct_count < 50, stable values
    is_likely_email: bool       # regex match on samples
    is_likely_timestamp: bool
    is_likely_currency: bool    # name contains amount/price/revenue
    is_likely_country: bool     # 2-char strings matching ISO 3166

@dataclass
class SuggestedCheck:
    detector_slug: str
    params: dict
    rationale: str              # one-line plain-English explanation
    confidence: float           # 0.0 to 1.0
    sample_size_used: int

def suggest_checks_for_column(profile: ColumnProfile,
                              use_llm: bool = True) -> list[SuggestedCheck]: ...
```

**Suggestion rules (deterministic core):**

| Profile signal | Suggested check(s) |
|---|---|
| `null_fraction > 0` on likely-PK | `null_fraction` with `fail_threshold: 0.0001` |
| `is_likely_pk` | `uniqueness` |
| `is_likely_fk` | `referential_integrity` to inferred parent |
| `is_likely_enum` | `set_membership` with sample-derived `allowed_values` |
| `is_likely_email` | `regex_match` with email pattern |
| `is_likely_timestamp` | `freshness_seconds_behind`, `value_in_range` with `max_value: now()` |
| `is_likely_currency` and `min_value < 0` | flag for review, suggest `value_in_range` with `min_value: 0` |
| `is_likely_country` | `set_membership` with ISO 3166 codes |
| numeric, heavy-tailed | `mad_outlier_fraction` |
| numeric, seasonality detected (autocorrelation) | `bocpd` |
| any column | baseline `completeness` and `row_count` |

**LLM-augmented layer:** runs as second pass when `use_llm=True` and API key present. Adds *semantic* suggestions based on column name + wiki context. Cached 7 days per column.

**Suggester API:**
- `GET /api/v1/columns/.../suggest` — ranked `list[SuggestedCheck]`, sorted by confidence desc. Cached 1h.

**`dqt metrics serve` CLI** — FastAPI app on configurable port (default 8090). Same auth model as dashboard (`DQT_DASHBOARD_TOKEN` or `DQT_METRICS_TOKEN` override). `/health` bypasses auth. `--generate-token` mutually exclusive with `--token`.

### 5.3 Frontend deliverables

**SPA scaffold:** Vite + React + TypeScript. Output to `dqt/web/metrics_app/static/`. Brand tokens as CSS variables:

```css
:root {
  --bg: #14181F;
  --bg-2: #1B2027;
  --bg-3: #232932;
  --line: #2A313B;
  --ink: #E6E9EE;
  --ink-mute: #9BA4AF;
  --ink-faint: #6C757F;
  --accent: #8FD1B2;
  --accent-deep: #5AA884;
  --pass: #8FD1B2;
  --warn: #D9B06A;
  --fail: #E08782;
  --font-mono: Consolas, "SF Mono", Menlo, monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
```

**Primitive components:** `Card`, `VerdictChip`, `LockupMark` (renders `質 dqt` kanji-first), `MetaLine` (the "01 / SECTION" pattern from the deck), `MonoText`, `Sparkline`, `EmptyState`, `Skeleton`.

**Top-bar component:** `質 dqt metrics` lockup in mint accent, Cmd-K input (non-functional in M1), theme switcher placeholder.

**Routing shell:** React Router with paths stubbed: `/` (Today, M3), `/ask` (M3), `/search` (M3), `/datasets` (M1), `/metric/:fqn` (M2), `/metric/:fqn/lineage` (M5), `/causal/review` (M5), `/subscriptions` (M4).

**Datasets page** (`/datasets`) — three-level browser:

1. Adapter list (left rail) — "Snowflake (prod)", "BigQuery (analytics)", "Local files"
2. Schema → table tree (middle rail) — collapsible with column count per table
3. Column list (main panel) — every column shows data type, recent null %, distinct count, and **a count badge: "3 checks" or "0 checks"**

Each column row clickable → expands inline:
- Type and stats (null %, distinct, samples)
- Existing checks as removable chips
- "+ Add check" → check picker modal
- "AI suggestions" section showing pending suggestions

**Check picker modal:**
- Tabs: "Suggested" (default) | "All detectors"
- Suggested tab: cards per suggestion with detector + params + rationale + confidence chip; "Accept" attaches immediately; "Customize" opens param editor
- All detectors tab: searchable, grouped by category (the v0.9.4 categorization: Completeness, Validity, Integrity, Schema, Univariate Outliers, Multivariate Outliers, Drift, Time Series, Custom)
- Param editor: form generated from detector parameter schema, sensible defaults, live preview chart against last 30 days where applicable

**Bulk "suggest checks for this table"** action at the table level. Runs suggester across all columns, presents batch reviewable list. Accept all / accept selected / reject all.

### 5.4 Tests (TDD enforced)

Before implementation:
- `tests/metrics/test_registry.py` — get, search, list, reload all specced
- `tests/checks/test_suggest.py` — fixture-based: 30 column profiles → expected suggestions
- `tests/web/test_datasets_api.py` — endpoint specs with auth on/off
- `tests/e2e/test_datasets_page.spec.ts` — Playwright E2E for the column browser and check picker

### 5.5 Acceptance criteria

- A user can browse adapter → schema → table → column entirely in the UI
- Each column shows accurate check count, 0 for unchecked
- AI suggestions appear for emails, enums, primary keys, currency, timestamps, country codes
- Suggestion latency: heuristic <2s, LLM-augmented <5s
- Accepting a suggestion creates the check, immediately visible
- Bulk-suggest generates >5 suggestions on a typical 20-column orders table
- Eval subagent confirms ≥70% accept rate on labeled fixtures
- v0.4.3 CI eval regressions pass
- 64 doc completeness tests pass

### 5.6 What this milestone unlocks

The primary metric-creation funnel. Before milestone 1, checks live in `checks.yaml`. After milestone 1, a new team can adopt dqt in an afternoon: walk their warehouse, accept AI suggestions per column, end up with hundreds of well-calibrated checks covering core tables. Every column with at least one check becomes a tracked metric.

**Ship as v1.1.0 release candidate after this milestone if pressure to release is high.**

---

## 6. Milestone 2 — The reconciliation engine and metric insight page

**The core capability lands here.** Surfaces minimal (one page) but the engine that powers everything is built.

### 6.1 Subagent decomposition

- `planner` — produce `docs/rfc/phase2/milestone-2.md`
- `backend-reconciliation` — `dqt.insights.explain_movement` orchestrator, Channel A scanner, Channel B routing
- `backend-narrative` — LLM pipeline with claim-citation post-processor
- `backend-mixshift` — first-class mix-shift decomposition engine
- `frontend-insight-page` — metric insight page with reconciliation bar, evidence table, audit drawer
- `eval-narrative` — labeled-fixture review of narrative quality (≥25 of 30 fixtures pass)

### 6.2 Backend deliverables

**`dqt.insights.explain_movement()`** — the orchestrator:

```python
def explain_movement(
    metric: Metric,
    window: tuple[datetime, datetime],
    *,
    method: Literal["auto", "granger", "pcmci_plus"] = "auto",
    use_llm: bool = True,
) -> MovementExplanation: ...
```

Auto-routing:
- 1-3 candidates → Granger pairwise (fast, simple)
- 4-15 candidates → PCMCI+ (controls for confounders)
- 16+ candidates → PCMCI+ with conditional independence pre-filtering

**Channel A scanner:** `dqt.insights.channel_a.scan(metric, window) -> list[DataIssue]`. Pulls upstream check verdicts within window, schema events, freshness/volume/completeness anomalies. Estimates magnitude contribution per issue with explicit ranges.

**Channel B orchestrator:** `dqt.insights.channel_b.analyze(metric, window, candidates) -> ChannelBReport`. Runs causal inference + mix-shift decomposition. Candidates default to all tracked metrics in catalog; configurable.

**Mix-shift decomposition:** `dqt.insights.mixshift.decompose(metric, window, dimensions)`. For aggregate metrics over dimensions, splits movement into "level changes within segments" vs "mix shifts between segments." First-class alongside causal inference.

**Reconciliation:** combines Channel A and Channel B into `MovementExplanation`. Conservative magnitude estimates with explicit ranges. `primary_channel` determined by which contribution range dominates.

**Narrative pipeline (`dqt.insights.narrative`):**
1. Render structured prompt from `MovementExplanation`
2. Call LLM via existing `dqt.wiki` Anthropic integration
3. Parse output, populate sentence_id → citations map
4. Post-process: every numeric claim must trace to evidence row
5. On rejection: regenerate up to 3 times, then fall back to template

**Streaming API:**
- `POST /api/v1/metrics/{fqn}/explain` — SSE response in 5 chunks:
  - Chunk 1 (~500ms): summary_paragraph
  - Chunk 2 (~2-5s): Channel A — data issues
  - Chunk 3 (~2-5s): Channel B — business drivers + mix-shift
  - Chunk 4 (~5-10s): ruled-out section
  - Final: computation_metadata + done sentinel

**Metric detail endpoint:**
- `GET /api/v1/metrics/{fqn}` — returns full Metric with cached narrative if available
- `GET /api/v1/metrics/{fqn}/series?lookback_days=` — time series
- `POST /api/v1/metrics/{fqn}/pin` — pin to homepage recents

**Caching:** key `(metric_fqn, window_hash, schema_version)`. TTL 6h business / 24h overnight. Invalidate on threshold-cross or schema change.

### 6.3 Frontend deliverables

**Metric insight page (`/metric/:fqn`):**

1. Header with display name, fqn, verdict chip, last-run, owner, pin, subscribe
2. **Current insight narrative** as headline content — streamed in, formatted as the brand "callout" pattern (left mint border on `--bg-2`, mono metadata above)
3. **Reconciliation bar** — horizontal stacked bar visualization of estimated Channel A (data) vs Channel B (business) contribution, with explicit range labels
4. **Time-window picker** — 7d, 30d, MTD, QTD, since release, custom range. Triggers narrative + chart refresh.
5. **Evidence table** — expandable rows per signal considered, columns: source, signal type, magnitude, evidence strength chip
6. **Time series chart** — Recharts, 90 days default, verdict markers, hover tooltips
7. **Lineage strip** — horizontal mini-graph, 3 up + 3 down, "See full lineage" link (disabled until M5)
8. **Recent incidents** — last 5, click → incident-focused narrative variant
9. **Active checks card** — list with thresholds, sparklines, "+ add check" → M1's picker
10. **Audit drawer** — click any sentence in narrative → side panel listing evidence rows that produced it

**Refresh narrative** action button — bypasses cache, regenerates on demand. Visible spinner during generation.

**Empty/error states** — when no causal candidates found, when LLM unavailable (shows fallback banner), when window too short for inference.

### 6.4 Tests (TDD enforced)

Before implementation:
- `tests/insights/test_explain_movement.py` — 5 canonical fixtures with expected primary_channel and top causes
- `tests/insights/test_channel_a.py` — data issue detection on known-bad-data fixtures
- `tests/insights/test_channel_b.py` — causal inference on labeled DAG fixtures
- `tests/insights/test_mixshift.py` — decomposition correctness on synthetic aggregate metrics
- `tests/insights/test_narrative.py` — claim-citation post-processor catches unsupported numbers
- `tests/insights/test_narrative.py` — fallback path triggers correctly
- `tests/e2e/test_metric_insight.spec.ts` — Playwright E2E: open metric → narrative streams in → reconciliation bar shows split → window picker refreshes → audit drawer cites evidence

### 6.5 Acceptance criteria

- Narrative quality: eval subagent confirms ≥25 of 30 fixtures pass ("reads as if analyst wrote it, no unsupported claims")
- Claim-citation post-processor catches every unsupported numeric claim across the 30-fixture eval
- First content visible <1s; full explanation streams <10s p95
- Mix-shift decomposition runs natively on aggregate metrics
- Reconciliation correctly identifies data-only, business-only, mixed cases on labeled fixtures
- `primary_channel` correct on 90% of labeled reconciliation fixtures
- Audit drawer cites correct evidence rows for every sentence
- v0.4.3 CI eval regressions pass

### 6.6 What this milestone unlocks

The differentiating capability lands here. Even with no feed or ask bar or digests, a user can open any tracked metric and get a written, reconciled, audit-backed answer to "why is this moving?" That alone is more than any current OSS or commercial tool delivers.

**Ship as v1.2.0 release candidate after this milestone.**

---

## 7. Milestone 3 — Today feed, Ask bar, and search

The product becomes pull-discoverable and push-scannable. Users land somewhere meaningful when they open dqt.

### 7.1 Subagent decomposition

- `planner` — produce `docs/rfc/phase2/milestone-3.md`
- `backend-feed` — feed ranking, scheduled regeneration
- `backend-ask` — natural language question resolution
- `backend-search` — fuzzy metric search
- `frontend-today` — Today feed homepage
- `frontend-ask-search` — Cmd-K modal, `/ask` page, `/search` page
- `eval-ask` — ≥80% resolution accuracy on 100-question evaluation set

### 7.2 Backend deliverables

**Feed ranking:** `dqt.insights.feed.rank(window: timedelta) -> list[FeedItem]`. Combines magnitude × statistical significance × executive-tier tag × novelty (time-decay since last surfaced) × engagement signal. Per-user personalization stub (M4 adds full personalization).

**Feed API:**
- `GET /api/v1/feed/today?lookback=24h&limit=20` — ranked items with attached narratives
- `GET /api/v1/feed/weekly?week=YYYY-WW` — weekly view
- `POST /api/v1/feed/items/{id}/reviewed` — mark item reviewed, removes from default view

**Background job:** nightly batch regeneration of narratives for every tracked metric. Runs as `dqt.insights.scheduler.refresh_all_narratives()`. Skips metrics with no significant movement to avoid LLM cost burn.

**Ask resolution (`dqt.insights.ask`):**
1. Extract metric reference (fuzzy match against catalog with confidence threshold)
2. Extract time window (parse phrases like "this week", "last 30 days", "since Apr 14")
3. Extract intent: `why` (explain movement) | `compare` (two metrics over window) | `list` (find metrics matching criteria)
4. If confidence below threshold → return disambiguation request, not a guess

**Ask API:**
- `POST /api/v1/ask` — body: `{question: str, user_context: dict}` → returns either `{type: "answer", explanation: MovementExplanation}` or `{type: "disambiguation", options: list[ClarifyOption]}`
- `POST /api/v1/ask/clarify` — user picks a disambiguation option, returns the answer

**Search API:**
- `GET /api/v1/metrics/search?q=&tags=&status=&owner=&limit=` — paginated `MetricSummary` list

### 7.3 Frontend deliverables

**Today feed (`/`)** — homepage:
- Ranked list of recent meaningful movements
- Each item: metric name + change, paragraph narrative, three evidence chips with sparklines, action row (dig deeper / share to slack / mark reviewed)
- Filters: by tag, by owner, by primary_channel ("show only data issues" / "show only business shifts")
- "Refresh feed" action
- Empty state when no significant movements

**Ask bar:**
- Cmd-K modal accessible from every page
- Dedicated `/ask` page with conversation history
- Input → result rendering: inline insight card with narrative, evidence chips, links to metric insight page
- Disambiguation UI: when ambiguous, show ClarifyOption cards with one-click resolution

**Search page (`/search`):**
- Search input with auto-complete
- Filter chips: tags, owner, current verdict status
- Results: rows with verdict dot, display name, fqn in mono, owner, last-run, click → metric insight page

### 7.4 Tests (TDD enforced)

- `tests/insights/test_feed_ranking.py` — ranking correctness on synthetic feed fixtures
- `tests/insights/test_ask_resolution.py` — 100-question eval set with expected resolutions
- `tests/insights/test_ask_disambiguation.py` — ambiguous questions trigger disambiguation, not guesses
- `tests/e2e/test_today_feed.spec.ts` — Playwright E2E: open homepage → feed renders → click item → metric insight page
- `tests/e2e/test_ask_bar.spec.ts` — Cmd-K from any page → ask question → insight card renders inline

### 7.5 Acceptance criteria

- Today feed surfaces meaningful items on representative data; engineering reviews 5 days of generated feeds for quality
- Ask bar resolves ≥80% of natural language questions correctly on the 100-question evaluation set
- Disambiguation feels natural — asks back rather than guessing when confidence below threshold
- Search returns results <100ms p95 over 1000-metric corpus
- Mark-reviewed persists, item disappears from default view, reappears with toggle
- v0.4.3 CI eval regressions pass

---

## 8. Milestone 4 — Subscriptions, digests, reactive notifications

The proactive surface. Most users will live in their Slack and email, never opening the UI.

### 8.1 Subagent decomposition

- `planner` — produce `docs/rfc/phase2/milestone-4.md`
- `backend-subscriptions` — subscription model, CRUD endpoints, threshold engine
- `backend-digest` — digest generation across cadences
- `backend-delivery` — Slack and email delivery
- `frontend-subscriptions` — subscription management UI
- `eval-digest` — digest quality review on representative fixtures

### 8.2 Backend deliverables

**Subscription model:**

```python
@dataclass
class Subscription:
    id: UUID
    user_id: str
    metric_fqns: list[str]
    cadence: Literal["daily", "weekly", "on_threshold"]
    delivery_channels: list[Literal["slack", "email"]]
    significance_threshold: float | None    # None = use per-metric default
    schedule_time: time                     # for daily/weekly digests
    created_at: datetime
```

**Subscription API:**
- `GET /api/v1/subscriptions` — list user's subscriptions
- `POST /api/v1/subscriptions` — create
- `PUT /api/v1/subscriptions/{id}` — update
- `DELETE /api/v1/subscriptions/{id}` — cancel
- `GET /api/v1/subscriptions/{id}/preview` — preview what the next digest will look like

**Significance threshold engine:** per-metric, learned from historical volatility. Default: 2σ from rolling 30-day baseline. Stored per metric, updates nightly. User-overridable.

**Reactive trigger:** when any metric crosses its threshold, immediately:
1. Run `explain_movement` for the metric
2. Identify subscribers whose threshold is crossed (per-metric thresholds may differ from global)
3. Generate per-subscriber notification with narrative
4. Push via configured channels within 5 minutes of threshold cross

**Scheduled digests:** cron-driven. `dqt.insights.digest.generate_daily()` and `generate_weekly()`. Each digest groups subscribed metrics by primary_channel (data issues, real shifts, no significant change), produces narrative summary, formats per channel.

**Delivery:**
- Slack: extends `dqt.bot`. Block Kit formatting for digests. Threading for follow-ups.
- Email: configurable SMTP. HTML + plain-text fallback. Per-section unsubscribe links.

### 8.3 Frontend deliverables

**Subscriptions page (`/subscriptions`):**
- List user's subscriptions with cadence, channels, threshold, last delivered timestamp
- Per-subscription edit modal: change metrics, cadence, threshold, channels
- "Subscribe" action surfaces on every metric insight page and feed item
- Preview pane: render exactly what the next digest will look like (uses current cached narratives)
- Digest history view: chronological list of past digests, click any → render in side panel

**"Subscribe" action** added to:
- Header of every metric insight page
- Action row of every Today feed item
- Result cards in ask responses

### 8.4 Tests (TDD enforced)

- `tests/insights/test_significance_threshold.py` — threshold learning on synthetic volatility fixtures
- `tests/insights/test_digest_daily.py` — daily digest content correctness on fixture metric set
- `tests/insights/test_digest_weekly.py` — weekly business review formatting
- `tests/insights/test_reactive_trigger.py` — threshold cross triggers within latency budget
- `tests/integration/test_slack_delivery.py` — Block Kit payload validity (no live Slack API call required)
- `tests/integration/test_email_delivery.py` — SMTP delivery via test server
- `tests/e2e/test_subscriptions.spec.ts` — Playwright: subscribe to a metric → see in subscriptions list → preview next digest

### 8.5 Acceptance criteria

- Subscribed user receives Slack message within 5 minutes of subscribed metric crossing threshold
- Daily and weekly digests auto-written, pass eval review on representative fixtures
- Subscription preferences persist and are user-configurable
- Email delivery works through configurable SMTP
- Slack Block Kit messages render correctly with deep links to metric insight page
- Preview pane matches actual delivered digest content
- v0.4.3 CI eval regressions pass

---

## 9. Milestone 5 — Lineage explorer, reviewer queue, hardening, v1.3.0

Supporting infrastructure for the data team plus release polish.

### 9.1 Subagent decomposition

- `planner` — produce `docs/rfc/phase2/milestone-5.md`
- `backend-lineage` — lineage subgraph API, nightly causal recomputation
- `backend-reviewer` — reviewer queue API, weighted scoring
- `frontend-lineage` — lineage explorer (Cytoscape-based)
- `frontend-reviewer` — reviewer queue page
- `frontend-polish` — Cmd-K everywhere, URL-stable share links, theme switcher
- `performance` — load testing, p95 optimization, Prometheus metrics
- `accessibility` — WCAG AA audit, focus management, screen reader review
- `docs` — Tutorial Chapter 11, API reference, STABILITY.md update
- `visual-QA` — every page at 3 viewport widths, overflow/overlap/contrast check

### 9.2 Backend deliverables

**Lineage API:**
- `GET /api/v1/lineage/graph?root=&direction=both&depth=3&include_causal=true` — subgraph centered on root
- `GET /api/v1/lineage/path?from=&to=` — shortest path between two metrics

**Nightly causal recomputation job:** runs across full lineage, persists `(source, target, strength, p_value)` to `dqt_causal_reviews_v2`. Initial run on first deploy. Incremental updates as new metrics are added.

**Reviewer queue:**
- `GET /api/v1/causal/review/queue?status=pending&limit=20` — paginated unreviewed edges
- `POST /api/v1/causal/review` — accept/reject with reviewer ID + notes
- `GET /api/v1/causal/review/stats` — accept rate, velocity, top reviewers

**Reviewer-weighted scoring:** accepted edges +0.2 weight in future causal queries; rejected edges filtered entirely.

**Prometheus metrics:** every API endpoint emits request count, latency p50/p95/p99, cache hit rate, narrative generation latency, LLM call count. Extends existing `dqt.metrics.prometheus` module.

### 9.3 Frontend deliverables

**Lineage explorer (`/metric/:fqn/lineage`):**
- Cytoscape with dagre layout
- Pan, zoom, drag-reposition (URL-encoded state)
- Node colors by verdict status; shapes by node type
- Lineage edges thin solid; causal edges dashed mint, thickness by strength
- Toggles: "Show causal edges" (off default), "Show downstream/upstream", depth slider 1-5
- Hover edge → tooltip with derivation SQL or causal metadata
- Click node → side panel with metric summary; double-click → metric insight page
- In-graph filter dims non-matching by fqn substring

**Reviewer queue (`/causal/review`):**
- Two-column: pending edges left with quick accept/reject icons
- Detail panel right: source → target chart, p-value, sample size, similar past decisions
- Accept / reject / "needs more info" buttons + optional notes textarea

**Polish:**
- Cmd-K everywhere — keyboard shortcut from any page
- Cmd-/ — help modal listing shortcuts
- URL-stable share links across all stateful pages (search query, lineage state, window picker)
- Theme switcher: dark default, light option respecting same semantics
- Empty/error/loading states for every list
- Microinteractions: hover, focus rings, transitions consistent

**Bundle splitting:** lineage page lazy-loaded (Cytoscape is heavy). Initial JS payload <500KB.

### 9.4 Performance budgets (verified by load test)

- Search response: <100ms p95
- Metric detail page first contentful paint: <500ms p95
- Narrative streaming first chunk: <1s p95
- Full narrative streamed: <10s p95
- Lineage 200-node render: <2s, panning at 60fps
- Today feed load: <800ms p95

**Load test target:** 50 concurrent users browsing + 5 concurrent explanations + nightly digest generation in background. p95 budgets met under this load.

### 9.5 Accessibility (WCAG AA)

- Color contrast: mint on dark passes verification; light theme verified independently
- Keyboard navigation: Cmd-K works without mouse; reviewer queue accept/reject works keyboard-only; tab order logical across every page
- Screen reader: causal explanation page reads in correct order; evidence chips have aria-labels; reconciliation bar has text alternative
- Focus management: modals trap focus; restore on close
- Reduced motion: prefers-reduced-motion respected for transitions

### 9.6 Documentation

- Tutorial Chapter 11: "Asking dqt why your metrics moved" — end-to-end walkthrough from setup to subscription
- `docs/api/insights.md` — full API reference for all Phase 2 endpoints
- README updated with the new positioning ("The why layer for BI")
- STABILITY.md updated with new public API surface
- CHANGELOG.md v1.3.0 entry summarizing the trajectory

### 9.7 Release

- Tag v1.3.0
- Publish to PyPI (verify sdist contains scripts/, examples/, docs/, tests/)
- Update dqt.dev with new positioning and tutorial link
- Cut release notes summarizing Phase 2

### 9.8 Acceptance criteria

- All pages pass WCAG AA
- p95 latency budgets met under load
- Tutorial Chapter 11 published, linked from README
- v0.4.3 CI eval suite passes — 30+ consecutive zero-regression releases
- Existing `dqt dashboard` continues to work unchanged
- Bundle size <1MB total, <500KB initial JS payload
- Visual QA subagent finds zero user-visible defects across all pages at 3 viewport widths

---

## 10. Cross-cutting concerns

### 10.1 Risk register

**LLM narrative quality is uneven.** Mitigation: claim-citation post-processor rejects unsupported claims and forces regeneration. Eval subagent reviews 30 fixtures per release. Template fallback always available.

**Reconciliation magnitude attribution is wrong.** Mitigation: conservative heuristic estimates with explicit ranges (not point estimates). User feedback "was this attribution correct?" feeds back into the model.

**Today feed surfaces noise.** Mitigation: importance scoring user-tunable; per-metric significance thresholds learn from historical volatility; "not interesting" feedback adjusts ranker.

**Ask bar misresolves questions.** Mitigation: disambiguation flow asks back; eval subagent measures resolution accuracy on 100-question set; confidence threshold gates auto-resolution.

**LLM costs scale poorly.** Mitigation: aggressive caching (TTL hours); bulk generation overnight; per-metric refreshes only on significance threshold cross, not on every page load.

**Existing checks.yaml workflows break.** Mitigation: UI writes to same store the YAML loader writes to. UI-created and YAML-created checks indistinguishable to runner. Existing workflows keep working unchanged.

**Scope creep.** Mitigation: no new detectors, no new adapters, no algorithm default changes, no dashboard regressions. Anything not in this brief defers to v1.4+.

### 10.2 Critical path and parallelization

```
M1 ──→ M2 ──→ M3 ──→ M4 ──→ M5
              │
              └──→ M5 (parallel with M3/M4)
```

- M1 must complete before anything else starts (no metrics, nothing to explain)
- M2 must complete before M3 (Today feed and ask depend on the engine)
- M3 must complete before M4 (subscriptions depend on feed/ask infrastructure)
- M5 can start in parallel with M3 or M4 — lineage and reviewer work is independent

### 10.3 Acceptance gates restated

Before any milestone is marked complete:

1. All milestone-specific acceptance criteria pass
2. v0.4.3 CI eval suite passes
3. 64 detector docs still ship (128/128 completeness tests pass)
4. No new detector defaults changed (v1.0 calibration contract holds)
5. Visual QA subagent has reviewed every new/changed page
6. Bundle size budget met
7. New public symbols documented in STABILITY.md
8. New API endpoints documented in docs/api/insights.md
9. CHANGELOG.md entry written

### 10.4 What NOT to do (claude code clarity)

- Do not add new detectors. 64 is the stable v1.x surface.
- Do not add new warehouse adapters. 6 is the stable v1.x surface.
- Do not change algorithm defaults. v0.9.3 calibration tables are public contracts.
- Do not modify the existing `dqt dashboard` product. It serves data engineers; the new product serves analysts and business users. They coexist.
- Do not refactor the v1.0 module structure. v1.x is a stability era.
- Do not skip the evaluation subagents. Suggestion quality, narrative quality, and ask resolution all have explicit eval gates.
- Do not narrate progress between tool calls. Plan → execute → verify → stop. Work, don't narrate.

### 10.5 What to ALWAYS preserve

- The v0.4.3 CI eval suite. 28 consecutive zero-regression releases. v1.3.0 must not break the streak.
- The detector docs from v0.9.3 (64 of 64). Public contract.
- The trimmed adapter table from v1.0.2 (6 real adapters). Don't reinflate.
- The deprecation-honoring discipline. v0.4.7 → v0.8.0 EventSource removal set the template; continue it.
- The single-purpose release discipline. Each milestone ships exactly its scope; no while-we're-in-there changes.

---

## 11. Positioning shift this unlocks

Before Phase 2: dqt is an OSS data quality library with causal inference as a unique feature.

After milestone 2: dqt is the **why layer** — the engine that explains any metric movement with two-channel reconciliation.

After milestone 3: dqt is a **self-service insights tool** — users open it daily, scan the feed, ask questions in natural language.

After milestone 4: dqt is the **analyst that's always on** — proactive Slack and email digests deliver insights without anyone having to open a dashboard.

The competitive set is no longer Monte Carlo / Anomalo / Bigeye. It's a new category nobody currently occupies: **AI-powered BI insights with auditable reconciliation between data quality and business drivers**. Looker, Sigma, Hex, MetricFlow get the "what." Monte Carlo and friends get "is it broken." dqt gets the "why" — which is the question the business is actually asking.

---

## 12. If only one milestone ships

**Milestone 2.** Without the two-channel reconciliation engine and the narrative pipeline, the rest is just UI. With milestone 2, even without the feed or ask bar or digests, a user can open any tracked metric and get a written, reconciled, audit-backed answer to "why is this moving?"

Milestone 1 is the prerequisite (no tracked metrics, no insights). Milestone 2 is the value. Milestones 3-5 are how the value reaches more users with less friction.

Cut order under scope pressure: 1 → 2 → 4 → 3 → 5. Skipping milestone 5 (lineage explorer + reviewer queue) is the least painful cut. Skipping milestone 4 (digests) destroys the proactive surface that makes dqt feel like an always-on analyst. Skipping milestone 3 (feed/ask) removes the entry points but the metric insight page from milestone 2 alone is still valuable.

---

## 13. Getting started — first actions for Claude Code

1. Read this document end to end. No skimming.
2. Spawn a planning subagent that produces `docs/rfc/phase2/overview.md` summarizing the architecture and milestone sequence, then `docs/rfc/phase2/milestone-1.md` with the detailed plan for the first milestone.
3. Verify the v0.4.3 CI eval suite passes on `main` before starting any work. If it doesn't, fix it first — the zero-regression streak is the non-negotiable baseline.
4. Create the `phase2-m1` branch.
5. Fan out the milestone 1 subagent tracks listed in section 5.1. Each track produces a PR against `phase2-m1`.
6. As each PR lands, run the acceptance gate checklist from section 0.
7. When all milestone 1 PRs are merged and gates pass, tag the work as v1.1.0 release candidate, decide whether to ship to PyPI now or continue to milestone 2.
8. Repeat for milestones 2-5.

Good luck. Build it well.

---

*— phase 2 brief, written 2026-05-16, based on iterative design with the dqt author across 28 releases of v1.x work.*

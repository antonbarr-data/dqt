# Insights API

The Insights API exposes metric definitions, time-series, and the two-channel movement explanation pipeline.

---

## Metric endpoints

### List metrics

```
GET /api/v1/metrics
```

Returns all registered metrics as a JSON array.

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `fqn` | `str` | Fully-qualified name -- e.g. `gigler.default.fct_orders.quality` |
| `display_name` | `str` | Human-readable label |
| `kind` | `str` | `ratio`, `count`, `sum`, or `model` |
| `dataset` | `str` | Source table name |
| `description` | `str` | Free-text description |
| `owners` | `list[str]` | Owner handles |
| `tags` | `list[str]` | Arbitrary tags |
| `unit` | `str \| null` | Display unit (e.g. `%`, `USD`) |
| `warn_threshold` | `float \| null` | Value below which verdict is `warn` |
| `fail_threshold` | `float \| null` | Value below which verdict is `fail` |
| `current_value` | `float \| null` | Latest observed metric value |
| `current_verdict` | `str \| null` | `pass`, `warn`, or `fail` |
| `last_run` | `str \| null` | ISO-8601 timestamp of last computation |
| `pinned` | `bool` | Whether the metric is pinned by the current session |

---

### Get metric detail

```
GET /api/v1/metrics/{fqn}
```

Same fields as above for a single metric. Returns 404 if not found.

---

### Get metric time series

```
GET /api/v1/metrics/{fqn}/series?lookback_days=30
```

Returns a synthetic weekly sinusoid + noise series seeded by `fqn`.

**Response**: array of `{ts, value, verdict}` objects. One entry per day over the requested lookback window.

---

### Pin a metric

```
POST /api/v1/metrics/{fqn}/pin
```

Marks the metric as pinned for the current session (in-memory). Returns `{fqn, pinned: true}`.

---

## Explain endpoint (two-channel SSE stream)

```
POST /api/v1/metrics/{fqn}/explain
Content-Type: application/json

{
  "lookback_days": 7,
  "force_refresh": false
}
```

Streams a `MovementExplanation` as Server-Sent Events. Results are cached for 6 hours per `(fqn, lookback_days)` pair. Pass `force_refresh: true` to bypass the cache.

### Event types

Events arrive in this order:

| Event type | When | Payload fields |
|------------|------|----------------|
| `start` | Immediately | `fqn`, `window_start`, `window_end` |
| `summary` | After LLM summary | `text` (plain-English paragraph), `primary_channel` (`data`, `business`, or `mixed`) |
| `channel_a` | After data analysis | `issues[]`, `estimated_contribution` (2-tuple `[low, high]`) |
| `channel_b` | After causal analysis | `drivers[]`, `estimated_contribution` (2-tuple `[low, high]`) |
| `ruled_out` | After filtering | `items[]` (candidates examined but not selected) |
| `done` | On completion | `explanation_id`, `citations` (sentence index -> evidence row IDs) |
| `error` | On failure | `message` |

### `channel_a.issues[]` fields

| Field | Type | Description |
|-------|------|-------------|
| `detector_slug` | `str` | Which detector fired |
| `verdict` | `str` | `fail` or `warn` |
| `contribution_low` | `float` | Lower bound of attributed contribution (fraction, 0-1) |
| `contribution_high` | `float` | Upper bound |
| `plain_english` | `str` | One-sentence human explanation |

### `channel_b.drivers[]` fields

| Field | Type | Description |
|-------|------|-------------|
| `cause` | `str` | Upstream metric FQN |
| `lag` | `int` | Granger-selected lag in periods |
| `p_value` | `float` | BH-adjusted p-value |
| `evidence_strength` | `str` | `none`, `weak`, `moderate`, or `strong` |
| `contribution_low` | `float` | Lower bound of attributed contribution |
| `contribution_high` | `float` | Upper bound |

### Narrative cache

- TTL: 6 hours from first computation
- Key: `(fqn, lookback_days)`
- `force_refresh: true` bypasses the cache and triggers a fresh LLM call
- Cache is invalidated on server restart (in-memory)

### Example (Python)

```python
import httpx, json

with httpx.stream("POST", "http://localhost:8000/api/v1/metrics/gigler.default.fct_orders.quality/explain",
                  json={"lookback_days": 7}) as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            evt = json.loads(line[6:])
            print(evt["type"], evt.get("text", "")[:80])
```

---

## Causal recomputation

```
POST /api/v1/causal/recompute
```

Runs Granger pairwise causality discovery over all registered metrics and queues significant edges (p < 0.05 after BH correction) for HITL review. Returns a summary of edges discovered and queued.

```
GET /api/v1/causal/recompute/status
```

Returns the timestamp of the last recomputation run and the current pending queue size.

# `custom.remote_check`

> *Remote endpoint score* — POSTs a sample of the current DataFrame to an external HTTP endpoint and uses the returned score as the dqt verdict, enabling checks implemented in any language or behind an internal API.

## What it does

At fit time, computes summary statistics (row count, column names, mean and std of all numeric columns) from the reference DataFrame and stores them along with the connection parameters. At score time, takes up to 1,000 rows from the current DataFrame, serialises them to JSON, and POSTs to the configured endpoint. For REST endpoints the body is `{"reference_stats": {...}, "current": [...rows...], "params": {...}}`. For GraphQL endpoints the body is a standard `{"query": "...", "variables": {...}}` envelope. The endpoint must return `{"score": float}` (optionally with a `"details"` key). The score is clipped to [0, 1] and fed into `_verdict()`. Network errors or missing `"score"` keys raise `RuntimeError` / `ValueError` — they are never silently ignored.

## When to use it

- Checks that require proprietary models or logic that cannot be shipped inside the dqt library (e.g. an internal fraud-score model, a compliance rule engine, a GraphQL API).
- Cross-language scoring: the scoring service can be in Go, Java, or Node.js — only the HTTP contract matters.
- When a check needs to call an external data source (e.g. look up a reference table not in the warehouse) — the external service has full access to its own data stores.
- Centralising expensive models: run a single scoring service that multiple dqt checks call, rather than loading the model in every worker.

## When not to use it

- Low-latency requirements — the HTTP round-trip adds at minimum tens of milliseconds per check run; use `callable_check` for in-process scoring.
- Checks that must run in offline/air-gapped environments — a network call to an external endpoint will fail.
- When the endpoint is not idempotent or has side effects — dqt may retry on transient failures; the endpoint must be safe to call multiple times.
- Sending more than 1,000 rows — the detector caps the payload at `_MAX_ROWS = 1000`. If the endpoint needs a full table scan, implement the scan server-side using the `reference_stats` for context.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `endpoint` | `str` | *(required)* | Full URL of the scoring endpoint (e.g. `http://fraud-api.internal/score`). |
| `params` | `dict` | `{}` | Arbitrary key-value pairs passed through to the endpoint in the `"params"` field. |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds. Raises `RuntimeError` on timeout. |
| `graphql_query` | `str \| None` | `None` | If set, switches to GraphQL mode. The POST body becomes a standard GraphQL envelope. |
| `graphql_variable` | `str` | `"rows"` | Variable name used to pass the row array in GraphQL mode. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.5` |
| `fail_threshold` | `0.75` |
| `direction` | `lower_is_better` |
| `score meaning` | Score returned by the external HTTP endpoint, clipped to [0, 1]; thresholds are overridable on the Check definition to match the endpoint's scoring semantics |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.custom.remote_check import RemoteCheckDetector

# fct_bookings: POST a sample to an internal fraud-score API.
# The API returns {"score": float} where score = fraction of rows flagged as suspicious.

ref = pd.DataFrame({
    "booking_id": range(1000),
    "gig_id": np.random.default_rng(10).integers(1, 5000, 1000),
    "buyer_id": np.random.default_rng(11).integers(1, 20000, 1000),
    "amount_paid_usd": np.random.default_rng(12).normal(90, 20, 1000).clip(5),
    "status": np.random.default_rng(13).choice(["completed", "pending", "cancelled"], 1000),
})

curr = pd.DataFrame({
    "booking_id": range(1000, 2000),
    "gig_id": np.random.default_rng(20).integers(1, 5000, 1000),
    "buyer_id": np.random.default_rng(21).integers(1, 20000, 1000),
    "amount_paid_usd": np.random.default_rng(22).normal(90, 20, 1000).clip(5),
    "status": np.random.default_rng(23).choice(["completed", "pending", "cancelled"], 1000),
})

det = RemoteCheckDetector(
    endpoint="http://fraud-api.internal/v1/score-bookings",  # full URL of the REST or GraphQL
                                                              # service (required)
    params={"model_version": "2.1", "threshold": 0.8},       # dict of extra query params merged
                                                              # into the request body
    timeout=15.0,  # 30s is generous for a scoring endpoint — lower to 5–10s for latency-sensitive
                   # pipelines; raises RuntimeError on timeout (never silently swallowed)
)
state = det.fit(ref)
# result = det.score(curr, state)   # uncomment when the endpoint is reachable

# GraphQL variant:
gql_det = RemoteCheckDetector(
    endpoint="http://fraud-api.internal/graphql",  # full URL of the GraphQL service
    graphql_query="""
        query ScoreBookings($rows: JSON!) {
            fraudScore(rows: $rows) { score details }
        }
    """,                          # provide the query string to switch to GraphQL mode; omit for REST
    graphql_variable="rows",      # name of the variable that receives the serialised rows (default "rows")
    timeout=15.0,                 # same guidance as above — lower for latency-sensitive pipelines
)
```

## Learn more

<!-- TODO: no simple YouTube explanation found — this is a dqt extension mechanism, not a published algorithm -->

## Implementation

[`packages/dqt/src/dqt/algorithms/custom/remote_check.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/custom/remote_check.py)

## Reference

- Extension point — no external algorithmic reference. HTTP contract documented in `remote_check.py` module docstring.

## Tests

`packages/dqt/tests/algorithms/custom/test_remote_check.py`

## When it works well

- Custom checks that require calling an external HTTP service (third-party validation APIs, internal microservice checks, external data enrichment).
- Useful for referential checks that span systems (e.g. validate IDs against an external registry).

## When it fails / Limitations

- Network latency and availability affect check reliability — implement retries and timeouts in the remote endpoint.
- External service failures produce `DetectorError`, not graceful verdicts; the remote service must be highly available if used in critical pipelines.
- Not suitable for high-frequency checks (per-row validation) — use it for aggregate checks only.
- FPR at defaults: entirely determined by the remote endpoint's logic.
- Minimum recommended sample: as required by the remote endpoint.
- FPR at defaults on clean normal data: user-defined.
- FPR at defaults on heavy-tailed data: user-defined.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Deterministic remote rule | 0 | 0 | Remote returns pass/fail directly |
| Statistical remote check | calibrate | calibrate | Calibrate against reference data |
| High-frequency use | N/A | N/A | Use local check or callable_check |

## Failure modes and known limits

`remote_check` introduces a network dependency into every check run. The detector itself is stateless on the dqt side; all scoring logic lives in the external endpoint. Reliability and correctness are entirely dependent on the remote service.

| Failure mode | Symptom | Fix |
|---|---|---|
| Network timeout | Check produces `RuntimeError` and the run is marked as `error` (not `fail`) | Set `timeout` conservatively; implement retries with exponential backoff in the remote service |
| Remote service returns non-JSON or missing `score` key | `ValueError` is raised; run is marked as `error` | Add response validation in the remote service; return `{"score": 1.0}` as a safe fallback on internal error |
| Remote service has side effects | Repeated calls (retries, re-runs) produce duplicate writes or consume quota | Design the endpoint to be idempotent; use request IDs if needed |
| Payload too large (> 1000 rows) | `_MAX_ROWS = 1000` truncates the payload; remote service receives a subset | Ensure the remote service is designed for samples, not full tables; implement full-table aggregation server-side |
| Score range mismatch | Remote returns scores outside [0, 1] (e.g. a probability not normalised, or a raw count) | The detector clips to [0, 1] silently; normalise in the remote service before returning |
| Authentication not handled | The remote endpoint requires auth but no auth headers are configured | Pass auth tokens via `params` dict and handle them in the endpoint; note the token appears in dqt's audit log |

### FPR table

| Remote service type | Expected FPR | Notes |
|---|---|---|
| Deterministic rule engine | 0% | Returns 0 or 1; no statistical approximation |
| ML scoring model | Depends on model calibration | Calibrate against labeled reference data |
| Statistical test endpoint | Equals the significance level used | Document which alpha the remote service targets |

### Threshold recommendations

- Default warn=0.5 / fail=0.75 assumes the remote service returns a fraction-like score in [0, 1].
- Override thresholds on the Check definition to match the remote service's scoring semantics.
- Implement a health-check endpoint on the remote service and use dqt's `freshness_seconds_behind` check to monitor it independently.

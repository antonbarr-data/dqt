# Remote check (`remote_check`)

**Group:** `custom` · **Kind:** `sample` · **Version:** `1` · **Min N:** 1

## What it computes

POSTs up to 1000 rows of the current DataFrame to an external HTTP/GraphQL endpoint and uses the returned `{"score": float}` as the verdict. Network errors raise `RuntimeError` and are never silently swallowed.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `endpoint` | `str` | `(required)` | Full URL of the scoring service |
| `params` | `dict` | `{}` | Arbitrary key-value pairs passed through to the endpoint |
| `timeout` | `float` | `30.0` | HTTP timeout in seconds (raises RuntimeError on timeout) |
| `graphql_query` | `str | None` | `None` | If set, switches to GraphQL mode |
| `graphql_variable` | `str` | `"rows"` | Variable name carrying the row array in GraphQL mode |

## Assumptions

- The endpoint is reachable and returns a JSON object with a `score` key in `[0, 1]`.
- The endpoint is idempotent — dqt may retry on transient failures.
- Authentication tokens are passed via `params` and appear in dqt's audit log.

## When it works well

- Cross-language scoring services (proprietary fraud model, compliance engine).
- Centralised expensive models that multiple dqt checks call.
- GraphQL endpoints that integrate with corporate data services.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Network timeout | Check produces RuntimeError; run is marked as error (not fail) | Set `timeout` conservatively; implement retries server-side |
| Missing `score` key | ValueError; run marked as error | Add response validation in the remote service |
| Side effects in remote service | Retries cause duplicate writes or quota burn | Make the endpoint idempotent; use request IDs |
| Payload too large (> 1000 rows) | Truncated payload; service sees a subset | Design the service for samples; aggregate full-table server-side |
| Score range mismatch | Endpoint returns a probability or raw count | Normalise to [0, 1] in the remote service |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | user-defined | Determined entirely by the remote endpoint |
| Lognormal | user-defined | Determined entirely by the remote endpoint |
| Poisson | user-defined | Determined entirely by the remote endpoint |
| Beta | user-defined | Determined entirely by the remote endpoint |
| Pareto | user-defined | Determined entirely by the remote endpoint |
| Exponential | user-defined | Determined entirely by the remote endpoint |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | user-defined |
| Lognormal | (default) | user-defined |
| Poisson | (default) | user-defined |
| Beta | (default) | user-defined |
| Pareto | (default) | user-defined |
| Exponential | (default) | user-defined |

## Citation

Extension point; no external algorithmic reference.

Implementation: `packages/dqt/src/dqt/algorithms/custom/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    detector_slug="remote_check",
    params={'endpoint': 'http://fraud-api.internal/v1/score-bookings', 'timeout': 15.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Introduces a network dependency into every check run.
- Capped at 1000 rows per payload.
- Not suitable for high-frequency checks or offline environments.

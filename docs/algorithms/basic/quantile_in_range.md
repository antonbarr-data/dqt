# Quantile in range (`quantile_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `PERCENTILE_CONT(q)` and returns 1.0 (fail) if outside `[min_val, max_val]`, otherwise 0.0. Standard tool for percentile-based SLAs.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `quantile` | `float` | `0.95` | Quantile in `(0, 1]` |
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Assumptions

- Sample size is large enough for the chosen quantile: ≥ `1/(1-q)` × 10 rows for p_q.
- Bounds are calibrated from historical quantile values, not raw data range.
- The warehouse's `PERCENTILE_CONT` interpolation matches your reference calibration.

## When it works well

- p95/p99 SLA monitoring (latency, response time).
- Stable quantile checks on heavy-tailed columns where mean is too noisy.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Insufficient N for extreme quantile | p99 requires ~100 rows; on small tables the estimate is unreliable | Use a quantile no more extreme than `1/(0.1 × N)` |
| Wrong quantile direction | Monitoring p5 instead of p95 misses the intended SLA | Verify the quantile matches the SLA direction |
| Seasonal quantile drift | p95 latency is higher at peak hours; static bounds fire during peaks | Set bounds from a 90-day rolling range |
| Heavy-tailed column | p95 varies run-to-run because extreme values dominate | Use a wider bound derived from the 30-day reference max of the quantile |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | 0% | Deterministic rule; bounds determine FPR exactly |
| Lognormal | 0% | Deterministic rule |
| Poisson | 0% | Deterministic rule |
| Beta | 0% | Deterministic rule |
| Pareto | 0% | Deterministic rule |
| Exponential | 0% | Deterministic rule |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | 0% |
| Lognormal | (default) | 0% |
| Poisson | (default) | 0% |
| Beta | (default) | 0% |
| Pareto | (default) | 0% |
| Exponential | (default) | 0% |

## Citation

No statistical reference; rule-based check on a quantile estimator (PERCENTILE_CONT).

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="api_requests",
    column_name="response_ms",
    detector_slug="quantile_in_range",
    params={'quantile': 0.95, 'min_val': 0.0, 'max_val': 2000.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Quantile estimate stability depends on N and on the warehouse's interpolation method.
- Static bounds are unreliable on strongly seasonal columns.

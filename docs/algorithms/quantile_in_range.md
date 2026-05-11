# `basic.quantile_in_range`

> *Quantile in bounds* — 1.0 if the specified quantile falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `PERCENTILE_CONT(q) WITHIN GROUP (ORDER BY col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if in range, 1.0 (fail) otherwise. No baseline is needed. Useful for SLA checks like "p95 response time must stay below 2 seconds".

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `quantile` | `float` | `0.95` | Quantile to compute, in `(0, 1]` |
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.5 |
| fail | 0.5 |
| direction | lower_is_better |

The warn and fail thresholds are both 0.5, so any violation (score = 1.0) is immediately a fail.

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.numeric_bounds import QuantileInRangeDetector

# QuantileInRangeDetector(
#     quantile=0.95,          # 0.95 (p95) is the most common choice for one-sided upper-tail checks;
#                             # use 0.99 for stricter tail monitoring;
#                             # use 0.50 for a robust median check
#     min_val=0.0,            # lower bound (rarely needed for tail checks)
#     max_val=float("inf"),   # maximum acceptable value at that quantile
# )

check = Check(
    schema_name="public",
    table_name="api_requests",
    column_name="response_ms",
    detector_slug="quantile_in_range",
    params={"quantile": 0.95, "min_val": 0.0, "max_val": 2000.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_quantile_values_to_be_between`
- Soda: `percentile` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`

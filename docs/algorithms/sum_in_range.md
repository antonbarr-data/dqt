# `basic.sum_in_range`

> *Sum in bounds* — 1.0 if `SUM(col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `SUM(col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if the sum is in range, 1.0 (fail) otherwise. No baseline is needed. Useful for financial reconciliation checks (e.g. total revenue must be between X and Y).

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
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
from dqt.algorithms.basic.numeric_bounds import SumInRangeDetector

# SumInRangeDetector(
#     min_val=0.0,            # minimum expected daily/batch sum (e.g. 10000 for a table
#                             # that should have at least $10k GMV/day)
#     max_val=float("inf"),   # ceiling to catch duplicate loads that would double the sum
# )

check = Check(
    schema_name="public",
    table_name="daily_revenue",
    column_name="revenue",
    detector_slug="sum_in_range",
    params={"min_val": 10000.0, "max_val": 10000000.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_sum_to_be_between`
- Soda: `sum` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`

## When it works well

- Financial reconciliation checks where the total sum of a column should match a known control total.
- Batch completeness checks (e.g. total loaded revenue should be within 1% of expected).

## When it fails / Limitations

- The sum grows with volume — if row count changes, the sum changes proportionally even without per-row errors; combine with `row_count_in_range` and use a ratio check instead for volume-independent monitoring.
- Sensitive to large individual values (outliers inflate the sum); monitor with both `sum_in_range` and `max_in_range`.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Fixed control total | exact bounds | exact bounds | Reconciliation use case |
| Volume-dependent sum | relative bounds | relative bounds | e.g. ± 1% of expected sum |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

# `basic.cardinality_in_range`

> *Cardinality in bounds* — 1.0 if `COUNT(DISTINCT col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `COUNT(DISTINCT col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if cardinality is in range, 1.0 (fail) otherwise. No baseline is needed. Useful for enum-like columns where the number of distinct values should be stable, or to detect runaway dimension tables.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `int` | `1` | Lower bound (inclusive) |
| `max_val` | `int` | `2^31` | Upper bound (inclusive) |

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
from dqt.algorithms.basic.numeric_bounds import CardinalityInRangeDetector

# CardinalityInRangeDetector(
#     min_val=1,          # for a status column with 5 known values use min_val=5;
#                         # for an ID column set to expected distinct users
#     max_val=2**31,      # flag unexpected cardinality explosions (e.g. a date column
#                         # suddenly having 1M distinct values = likely timestamp instead of date)
# )

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="status",
    detector_slug="cardinality_in_range",
    params={"min_val": 3, "max_val": 6},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_unique_value_count_to_be_between`
- Soda: `distinct_count` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`

## When it works well

- Categorical or ID columns where the number of distinct values should remain within expected bounds.
- Detects new categories appearing (cardinality increase) or category collapse (cardinality decrease).

## When it fails / Limitations

- High-cardinality columns (user IDs, session IDs) have cardinality that scales with row count — set bounds relative to expected sample size rather than absolute values.
- New legitimate categories (new product lines, new country codes) will trigger the upper bound; review and update bounds when the business evolves.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Low-cardinality enum | exact expected bounds | exact expected bounds | e.g. status has 4 values |
| Growing high-cardinality | relative to row count | relative to row count | e.g. max=row_count |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

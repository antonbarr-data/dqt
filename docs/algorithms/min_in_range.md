# `basic.min_in_range`

> *Min in bounds* — 1.0 if `MIN(col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `MIN(col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if the minimum is in range, 1.0 (fail) if it is not. No baseline is needed.

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
from dqt.algorithms.basic.numeric_bounds import MinInRangeDetector

# MinInRangeDetector(
#     min_val=0.0,            # hard floor (e.g. 0.01 for amounts, 1 for IDs)
#     max_val=float("inf"),   # caps the minimum if it should never be too high
# )

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="min_in_range",
    params={"min_val": 0.0, "max_val": 1000000.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_min_to_be_between`
- Soda: `min` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`

## When it works well

- Numeric columns where the minimum value should stay above a floor (e.g. price > 0, quantity ≥ 1, duration_ms ≥ 0).
- Catches negative or zero values in strictly positive columns.

## When it fails / Limitations

- Legitimate minimum values at the edge of the range (e.g. a genuine zero-value transaction) can fire the check; set bounds with business domain knowledge.
- For sparse columns, the minimum may vary significantly with sample size; consider using `quantile_in_range` at the 1st percentile for more stable monitoring.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Hard lower bound | (default) | (default) | STAT_SCALES defaults |
| Near-zero floor | 0 | 0 | Exact zero tolerance |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

`min_in_range` checks the single minimum value in the sample. Like `max_in_range`, the minimum is highly sensitive to single extreme values and to sample size. On small samples the minimum is an unstable statistic; use `quantile_in_range` at p0.1 for more stable lower-tail monitoring.

| Failure mode | Symptom | Fix |
|---|---|---|
| Single refund or credit creates a negative value | One legitimate credit note fires the check | If credits are valid, set min_val to the minimum allowed credit amount (e.g. -10000) |
| Sample-size dependence | As N grows, the minimum decreases even without distribution change | Use `quantile_in_range` at p0.01 which is more stable |
| Zero-value records from a default fill | An ETL default-fill produces zeros in an otherwise positive column | Detect at the ETL layer; or set min_val=0 and treat zeros as valid |
| Sentinel values from upstream (e.g. -1 = "unknown") | Sentinel fires the check legitimately | Either filter sentinels upstream or use a `sql_assertion_violation` that handles sentinels explicitly |
| Late-arriving records with early timestamps | A late-arriving record has a very old date which becomes the new minimum | Filter by loaded_at not event_at for time-based min checks |

### FPR table

| Data shape | Expected FPR (correct bounds) | Notes |
|---|---|---|
| Normal (mu=100, sigma=10) with min_val=50 (5 sigma below) | ~0% | Extremely rare for N=100k sample |
| Uniform [0, 1] with min_val=0 | 0% | Hard floor is a domain constant |
| Pareto (heavy left tail) | Variable | Set min_val from historical 0.01st percentile |

### Threshold recommendations

- For strictly positive columns (prices, durations, IDs): set min_val=0 and treat any negative as a failure.
- For columns with a known domain floor (e.g. rating >= 1): set min_val to the domain minimum exactly.
- For columns without a hard domain floor: derive min_val from the historical 0.1st percentile of the reference window and subtract 3 standard deviations of that statistic.

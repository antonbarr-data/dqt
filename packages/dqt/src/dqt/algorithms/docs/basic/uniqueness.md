# Uniqueness (`uniqueness`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `COUNT(DISTINCT col) / COUNT(*)`. 1.0 means every value is unique; lower values indicate duplicates. Direction is `higher_is_better`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- The column is expected to be unique (PK, natural key, or near-unique identifier).
- Sampling may underestimate duplicate counts; full-table runs for hard PK enforcement.

## When it works well

- Primary-key columns where any duplicate is a real bug.
- Natural keys with a small tolerance for legitimate duplicates.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Natural duplicates | Category/status columns legitimately have few unique values | Use `cardinality_in_range` instead; uniqueness is not the right check |
| Sampling misses rare duplicates | 100k sample of a 50 M-row table reports 100% unique while duplicates exist | Run against the full table for critical PKs |
| NULL handling | NULL values may or may not count toward distinct values depending on warehouse | Verify warehouse semantics; pair with `null_fraction` |

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

No statistical reference; rule-based check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="users",
    column_name="email",
    detector_slug="uniqueness",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- `COUNT(DISTINCT)` is expensive on large tables; use approximate-distinct (HLL) for cost-sensitive monitoring.
- Sample-based runs miss rare duplicates.

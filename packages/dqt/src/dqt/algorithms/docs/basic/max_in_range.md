# Max in range (`max_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `MAX(col)` and returns 1.0 (fail) if it falls outside `[min_val, max_val]`, otherwise 0.0. Both `warn` and `fail` thresholds are 0.5 so any violation is immediately a fail.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Assumptions

- A hard physical or business ceiling exists for the column (percentages, ratings, fixed-range IDs).
- Single-value extreme spikes are operationally relevant.

## When it works well

- Bounded columns with a known maximum (rating ≤ 5, discount ≤ 1.0).
- Catching corruption sentinels (`9999999`) and overflow values.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Single legitimate outlier | One real but valid high-value transaction fires the check | Verify the outlier; widen the bound or switch to `quantile_in_range` at p99 |
| Sample-size growth raises expected max | As N grows the maximum creeps up even on stable distributions | Use `quantile_in_range` at p99.9 instead |
| Data corruption introduces sentinel values | Max jumps to a garbage value (e.g. `-1`, `9999999`) | Set both lower and upper bounds to catch sentinels and overflows |
| Stale bounds after business change | Pricing limits raised but bounds were not updated | Review bounds after planned pricing or scale changes |

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

No statistical reference; rule-based bound check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="orders",
    column_name="discount_pct",
    detector_slug="max_in_range",
    params={'min_val': 0.0, 'max_val': 1.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Maximum is the most variable order statistic; unstable on small samples.
- Not appropriate for heavy-tailed columns without a domain ceiling — use `quantile_in_range` at p99.

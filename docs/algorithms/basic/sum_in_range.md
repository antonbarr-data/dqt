# Sum in range (`sum_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `SUM(col)` and returns 1.0 (fail) if outside `[min_val, max_val]`, otherwise 0.0. Used for financial reconciliation and batch-completeness checks.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Assumptions

- The expected sum is known (control total, reconciliation target) or can be calibrated from history.
- Row count is monitored alongside (`row_count_in_range`) so volume coupling can be diagnosed.
- Outliers are monitored alongside (`max_in_range`) so extreme-value inflation is detected.

## When it works well

- Financial reconciliation against a control total.
- Daily batch completeness checks (total loaded revenue within ±1% of expected).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Volume coupling | Row count grows → sum grows → upper bound fires on stable per-row values | Pair with `row_count_in_range`; use `numeric_mean` per row for volume-independent monitoring |
| Single large outlier inflates sum | One corrupt record fires the upper bound | Pair with `max_in_range`; investigate before widening |
| Duplicate load | ETL loads the same period twice; sum doubles | Set `max_val` at 1.1× expected to catch duplicates |
| Seasonal volume change | Sum drops 30% during Q4 holidays | Set bounds from a 90-day seasonal range |
| Currency / unit change | Upstream switched USD → cents; sum is 100× larger | Monitor with `numeric_mean` per row; 100× jump on both is the signal |

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

No statistical reference; rule-based check on an aggregate.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="daily_revenue",
    column_name="revenue",
    detector_slug="sum_in_range",
    params={'min_val': 10000.0, 'max_val': 10000000.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Highly sensitive to outliers and row-count changes; always paired with companion checks.
- Floating-point precision issues for large many-row sums.

# Monotonicity (`monotonicity`)

**Group:** `basic` · **Kind:** `sample` · **Version:** `1` · **Min N:** 2

## What it computes

Takes the first numeric column of the sampled DataFrame, computes consecutive differences with `numpy.diff`, and verifies the sequence is non-decreasing (or non-increasing). Returns 0.0 if monotonic, 1.0 otherwise.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `direction` | `str` | `"increasing"` | `increasing` (non-decreasing) or `decreasing` (non-increasing) |

## Assumptions

- The sample query orders rows by the intended sequence column.
- Backfills and late-arriving rows are handled outside the check or tolerated via warn-only mode.
- The column has well-defined ordering semantics (sequence ID, version, monotonic timestamp).

## When it works well

- Auto-increment IDs, version numbers, monotonically increasing timestamps.
- Event sequence tables where out-of-order rows indicate ETL bugs.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Sample not ordered by sequence column | The check evaluates random row order and passes/fails non-deterministically | Always specify `ORDER BY sequence_col` in the sample query |
| Backfills / late-arriving rows | A historical record inserted after newer rows produces a dip | Use `warn` instead of `fail` for tables with known late arrivals |
| Cumulative metric that resets | A running total resets to zero at the start of each period | Scope to a single period window or exclude reset points |
| Composite sort key needed | Natural order requires sorting by `(date, id)` not just `id` | Use `sql_assertion_violation` with a `LAG()` window function |

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

No statistical reference; deterministic ordering check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="events",
    column_name="event_sequence_id",
    detector_slug="monotonicity",
    params={'direction': 'increasing'},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Depends entirely on the row order returned by the sample query.
- Cannot detect missing IDs within a monotonic sequence; pair with `uniqueness`.

# Volume drift (`volume`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `|current_count / baseline_count - 1|` — fractional deviation of current row count from the baseline. 0.0 means no change.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- Baseline window is representative (re-fit when stale).
- Row count is a meaningful data quality signal for this table.
- Variability of row count is moderate; high-variance tables need wider thresholds.

## When it works well

- Daily-loaded tables with stable expected row counts.
- Detecting pipeline failures (volume drops) or duplicate loads (volume spikes).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Baseline fitted on atypical period | Baseline includes a campaign; normal days fire warn | Re-fit on a representative 30-day window |
| Seasonal growth | Table grows 5% per month; baseline becomes stale | Re-fit quarterly or use a rolling baseline |
| Planned maintenance window | Volume drops to 0 during planned maintenance | Snooze the check or exclude maintenance windows from baseline |
| Duplicate load | Count doubles; score correctly fires at 1.0 | Verify by inspecting `composite_uniqueness` simultaneously |
| Single-shard partition failure | One shard fails; count drops by 1/N | Pair with `freshness_seconds_behind` for partition-level diagnosis |

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

No statistical reference; fractional-deviation check on a fitted baseline.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="volume",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Requires a stable baseline; volatile tables produce noisy scores.
- Static deviation thresholds are too tight for highly variable tables — use `stl_residual_zscore` for trend-aware monitoring.

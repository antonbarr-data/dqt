# Median in range (`median_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `PERCENTILE_CONT(0.5)` and returns 1.0 (fail) if the median falls outside the declared bounds, otherwise 0.0. The median is robust to outliers, making it preferred over the mean for skewed columns.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Assumptions

- The median is a meaningful summary for the column (continuous or ordinal).
- Bounds are calibrated from a representative historical window (30–90 days).

## When it works well

- Heavy-tailed columns (revenue, latency) where mean monitoring would be too noisy.
- Detecting silent pricing drift on a marketplace.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Stale bounds after seasonal shift | Median drifts seasonally but bounds were set on non-seasonal data | Set bounds from a full-year historical percentile range |
| Multimodal distribution | Median sits in a low-density trough between modes and jumps between them | Segment the check by a dimension column |
| Sparse data (< 30 rows) | PERCENTILE_CONT estimate is noisy; median can jump significantly | Increase sample size or widen bounds |
| Bounds not updated after pricing change | A planned price change moves the median outside stale bounds | Review bounds as part of any planned business change |

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

No statistical reference; rule-based bound check on a quantile estimator.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="median_in_range",
    params={'min_val': 10.0, 'max_val': 500.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Robust to outliers but still requires correct bounds.
- Not informative on bimodal columns where the median lands between modes.

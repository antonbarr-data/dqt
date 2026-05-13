# Value in range (`value_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Evaluates `col < min_val OR col > max_val` per row and returns the violation fraction. 0.0 means all values are within bounds.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `-inf` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Assumptions

- Bounds are known business or physical constraints (percentages, ratings, ID ranges).
- Sample is representative of the population (no biased filtering).

## When it works well

- Bounded numeric columns (percentages 0–1, ratings 1–5).
- Detecting individual out-of-range values that aggregates miss.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Range drift over time | Legitimate data expansion beyond historical range fires as a violation | Use `calibrate_from_history()` to auto-expand bounds |
| Exclusive vs inclusive bounds | Off-by-one on boundary values | Verify `inclusive_lower` / `inclusive_upper` match the business rule |
| Bounds not updated after business change | A new product line expanded the legitimate range but bounds were stale | Review bounds after any planned scale change |

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
    column_name="amount",
    detector_slug="value_in_range",
    params={'min_val': 0.0, 'max_val': 100000.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Doesn't catch distribution changes inside the valid range; pair with `wasserstein_1` / `ks_pvalue`.
- Sensitive to bound staleness on growing tables.

# Cramér's V (`cramers_v`)

**Group:** `info` · **Kind:** `sample` · **Version:** `1` · **Min N:** 50

## What it computes

Builds a 2×K contingency table (reference vs current) and computes V = sqrt(chi² / N). Returns a bounded effect-size measure in `[0, 1]`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- The column is categorical.
- Sample size ≥ 50 per window; bias correction reduces but does not eliminate small-N inflation.
- Cardinality is moderate (2–50 distinct values).

## When it works well

- Categorical drift magnitude — comparable across columns and sample sizes.
- Summarising categorical drift in dashboard KPIs.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Small N (< 50) | V is upward-biased even after correction | Require N ≥ 50; reduce check frequency or increase window |
| High-cardinality column (> 50 distinct values) | Many low-count cells inflate chi² and V | Group rare categories into 'other' before scoring |
| Unseen categories in current window | Chi² has a zero cell for the unseen category | Use `chi_square_drift` with `handle_unseen=add_small_count` |
| Asymmetric window sizes | V sensitive to minimum N | Subsample to equal sizes before comparing |
| Binary column with heavy class imbalance | V overstates drift when the minority class shifts | Report alongside absolute count differences |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | N/A | Categorical detector |
| Lognormal | N/A | Categorical detector |
| Poisson | ~5-7% | Low-cardinality integer |
| Beta | N/A | Continuous |
| Pareto | N/A | Continuous |
| Exponential | N/A | Continuous |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | N/A |
| Lognormal | (default) | N/A |
| Poisson | (default) | ~5-7% |
| Beta | (default) | N/A |
| Pareto | (default) | N/A |
| Exponential | (default) | N/A |

## Citation

Cramér, H. (1946). *Mathematical Methods of Statistics*. Princeton University Press. (§21.6)

Implementation: `packages/dqt/src/dqt/algorithms/info/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="dim_sellers",
    column_name="tier",
    detector_slug="cramers_v",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Effect-size measure; for hypothesis testing use `chi_square_drift`.
- Upward-biased at small N even with bias correction.

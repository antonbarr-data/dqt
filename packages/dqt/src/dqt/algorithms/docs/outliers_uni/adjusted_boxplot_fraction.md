# Adjusted boxplot (medcouple) (`adjusted_boxplot_fraction`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 20

## What it computes

Computes medcouple MC of the reference. For MC ≥ 0 widens the upper fence exponentially (`Q3 + h·exp(3·MC)·IQR`) and shrinks the lower; for MC < 0 the adjustment is mirrored. Returns the fraction of current values outside the adjusted fences.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `h` | `float` | `1.5` | IQR multiplier (Tukey's k); standard 1.5 = inner fences |

## Assumptions

- Numeric column with mild to moderate skewness (|MC| ≤ 0.5).
- Sample size ≥ 20 for stable medcouple.
- Symmetric Tukey IQR fences would over-flag the dominant tail.

## When it works well

- Skewed columns (revenue, latency, session duration) where IQR fence over-flags the heavy tail.
- Non-parametric — no distributional assumptions; adapts to column asymmetry.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Extremely heavy skewness (|MC| > 0.6) | Exponential correction becomes unstable | Use `double_mad_outlier_fraction` |
| Multimodal reference | MC estimates median of a mixed distribution; fences may not span modes | Segment data before scoring |
| N < 50 | Medcouple noisy | Increase baseline window |
| Symmetric data | Medcouple = 0; reduces to standard IQR | Use `iqr_fence` for clearer semantics |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.7-1% | Medcouple ~0; reduces to standard IQR |
| Lognormal | ~0.5-1% | Medcouple correction handles right tail well |
| Poisson | ~0.5% | Discrete; mild skew |
| Beta | ~1% | Bounded; symmetric |
| Pareto | ~1-2% | Very heavy tail; correction stretches but holds |
| Exponential | ~0.5-1% | Right-skew; correction works well |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.7-1% |
| Lognormal | (default) | ~0.5-1% |
| Poisson | (default) | ~0.5% |
| Beta | (default) | ~1% |
| Pareto | (default) | ~1-2% |
| Exponential | (default) | ~0.5-1% |

## Citation

Hubert, M. & Vandervieren, E. (2008). *An adjusted boxplot for skewed distributions*. Computational Statistics & Data Analysis, 52(12), 5186–5201.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_uni/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="adjusted_boxplot_fraction",
    params={'h': 1.5},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Unstable for extreme skewness; switch to `double_mad_outlier_fraction`.
- Medcouple is O(n log n); slightly slower than plain IQR.

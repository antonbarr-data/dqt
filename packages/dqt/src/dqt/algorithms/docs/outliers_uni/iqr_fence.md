# IQR fence (Tukey) (`iqr_fence`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 20

## What it computes

Computes Q1, Q3, IQR from the reference. Defines fences `[Q1 - k·IQR, Q3 + k·IQR]` and returns the fraction of current values outside the fences. k=1.5 = inner fences, k=3.0 = outer.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `k` | `float` | `1.5` | IQR multiplier; 1.5 = inner fences, 3.0 = outer fences |

## Assumptions

- Sample size ≥ 20 for stable quartile estimates.
- Distribution is unimodal; bimodal columns inflate IQR.
- Symmetric fence is acceptable; for asymmetric data prefer `adjusted_boxplot_fraction`.

## When it works well

- Quick non-parametric outlier check on any unimodal numeric column.
- Exploratory analysis or sanity check alongside a more powerful detector.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Symmetric IQR on asymmetric data | Lower fence fires constantly on revenue/latency right tail | Use `adjusted_boxplot_fraction` |
| Sparse data (N < 30) | Quartile estimates noisy; fences unstable | Increase sample size |
| Constant value (IQR=0) | All deviations flagged | Handle constant columns with `uniqueness` upstream |
| Uniform distribution | IQR covers too little; normal values flagged | Increase `k` to 3.0 |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.7% | Standard Tukey rule |
| Lognormal | ~5-20% | Right skew pushes points past upper fence |
| Poisson | ~0.5% | Discrete; mild |
| Beta | ~0.5% | Bounded |
| Pareto | ~10-25% | Very heavy tail; constant alerts |
| Exponential | ~3-8% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.7% |
| Lognormal | (default) | ~5-20% |
| Poisson | (default) | ~0.5% |
| Beta | (default) | ~0.5% |
| Pareto | (default) | ~10-25% |
| Exponential | (default) | ~3-8% |

## Citation

Tukey, J.W. (1977). *Exploratory Data Analysis*. Addison-Wesley. (Chapter 2: boxplots and fences.)

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
    detector_slug="iqr_fence",
    params={'k': 1.5},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Symmetric fences; over-flag dominant tail on skewed data.
- Sensitive to contaminated reference (high IQR masks true anomalies).

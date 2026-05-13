# Page-Hinkley (`page_hinkley`)

**Group:** `timeseries` · **Kind:** `sample` · **Version:** `1` · **Min N:** 20

## What it computes

Computes reference mean μ and σ. Runs PH_t = Σ(x_i − μ − δ); alarms when `PH_t − min(PH) > λ`. Reports normalised score `(PH − min_PH) / λ`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `delta` | `float` | `0.005` | Tolerance in σ units; absorbs small fluctuations |
| `lambda_` | `float` | `100.0` | Alarm threshold in σ-accumulated units |

## Assumptions

- Univariate numeric stream; one-directional monitoring.
- δ and λ are scaled by σ at fit time, so the same parameters work across magnitudes.
- Reference is stationary (no trend).

## When it works well

- Detecting sustained upward (or downward) mean shifts in a streaming metric.
- Online pipelines with O(1) memory per step.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Bidirectional shifts in one pass | Standard PH only detects upward shifts | Use two instances or the two-sided variant |
| Abrupt spike-and-recover anomalies | PH accumulates slowly; not designed for transient outliers | Use `stl_residual_zscore` or `generalized_esd` |
| Non-stationary reference (strong trend) | Continuous accumulation; PH alarms without a real change-point | Detrend first |
| Heavy-tailed distributions | Extreme values dominate the cumulative sum | Winsorise or use MAD normalisation |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~1-3% | Controlled by λ |
| Lognormal | ~5-10% | Heavy tail inflates cumulative sum |
| Poisson | ~2-3% | Discrete; well behaved |
| Beta | ~2-3% | Bounded |
| Pareto | ~10-15% | Heavy tail; winsorise first |
| Exponential | ~5-8% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~1-3% |
| Lognormal | (default) | ~5-10% |
| Poisson | (default) | ~2-3% |
| Beta | (default) | ~2-3% |
| Pareto | (default) | ~10-15% |
| Exponential | (default) | ~5-8% |

## Citation

Hinkley, D. V. (1971). Inference about the change-point from cumulative sum tests. *Biometrika*, 58(3), 509–523.

Implementation: `packages/dqt/src/dqt/algorithms/timeseries/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    column_name="avg_price_usd",
    detector_slug="page_hinkley",
    params={'delta': 0.005, 'lambda_': 100.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- One-directional by default.
- Mean-shift detector only; pair with variance check for full coverage.

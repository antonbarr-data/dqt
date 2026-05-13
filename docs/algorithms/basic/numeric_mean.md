# Numeric mean (Z-shift) (`numeric_mean`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 30

## What it computes

Fits the reference mean and stddev with `AVG` and `STDDEV`. Reports `|current_mean - baseline_mean| / baseline_stddev` — number of baseline sigmas the current mean has drifted.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- Reference window is representative and not contaminated by outliers that inflate stddev.
- Column distribution is approximately Gaussian — heavy-tailed columns produce noisy means.
- Sample size in the current window is ≥ 30 for stable mean estimation.

## When it works well

- Near-Gaussian KPIs (page views, count-of-event, normalised scores).
- Detecting level shifts on cleanly distributed columns.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Outliers in reference inflate baseline stddev | Real mean shifts score below 2 sigma and go undetected | Use a cleaned reference window with outliers removed |
| Outliers in current inflate the current mean | One large transaction moves the mean outside the band | Switch to `median_in_range` on heavy-tailed columns |
| Seasonal mean drift | Mean drifts seasonally but is not a data quality issue | Re-fit baseline seasonally; or use a drift detector with same-period windows |
| Near-zero baseline stddev | Z-score becomes infinite for any deviation | Add a minimum stddev guard; use `value_in_range` for near-constant columns |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~4.6% | Theoretical two-sided 2-sigma FPR |
| Lognormal | ~8-12% | Right-skew inflates upward false positives |
| Poisson | ~5% | Approximately normal for large lambda |
| Beta | ~5% | Bounded; moderate tail effects |
| Pareto | ~15-20% | Heavy tail; mean is volatile — use median instead |
| Exponential | ~6-8% | Skewed; mean inflated by tail |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~4.6% |
| Lognormal | (default) | ~8-12% |
| Poisson | (default) | ~5% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~15-20% |
| Exponential | (default) | ~6-8% |

## Citation

No single paper; standard Z-score-of-mean monitoring. See Press et al. 1992 'Numerical Recipes' for the Z-score derivation.

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
    detector_slug="numeric_mean",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Inherits Z-score limitations: over-sensitive on heavy-tailed data.
- Sample mean variance scales with 1/sqrt(N); small batches produce noisy scores.

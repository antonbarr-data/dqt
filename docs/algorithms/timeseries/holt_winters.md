# Holt-Winters anomaly (`holt_winters`)

**Group:** `timeseries` · **Kind:** `sample` · **Version:** `1` · **Min N:** 14

## What it computes

Trains `statsmodels` Holt-Winters with additive trend + additive seasonality on the reference. At score time forecasts n steps ahead with ±z × σ_resid prediction interval (default 99%). Returns fraction of current values outside the interval.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period` | `int` | `7` | Seasonal period in observations |
| `alpha` | `float` | `0.99` | Coverage for the prediction interval |

## Assumptions

- Series has a clear seasonal period (default 7 for daily data with weekly seasonality).
- Reference contains ≥ 2 × period observations.
- Trend and seasonality are roughly additive on the original scale.

## When it works well

- Weekly-seasonal metrics (daily sessions, daily bookings, daily active users).
- Lower-complexity alternative to Prophet when holiday calendars are not needed.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Non-seasonal data | Additive seasonality assumption causes over-smoothing; residuals lose meaning | Use `cusum` or `page_hinkley` |
| < 2 full seasonal periods | Cannot initialise the seasonal component | Collect more history |
| Level shifts in reference | Model adapts slowly; streak of false positives after a real shift | Use BOCPD for abrupt level changes |
| Wrong period parameter | Misattributes seasonal patterns as anomalies | Verify period matches data cadence |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~2-5% | Well-calibrated on seasonal Gaussian residuals |
| Lognormal | ~10-15% | Heavy tail inflates residuals |
| Poisson | ~3-5% | Discrete; mild inflation |
| Beta | ~3-5% | Bounded |
| Pareto | ~15-25% | Heavy tail; do not use without log transform |
| Exponential | ~8-12% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~2-5% |
| Lognormal | (default) | ~10-15% |
| Poisson | (default) | ~3-5% |
| Beta | (default) | ~3-5% |
| Pareto | (default) | ~15-25% |
| Exponential | (default) | ~8-12% |

## Citation

Holt, C. C. (1957). Forecasting seasonals and trends by exponentially weighted averages. ONR Memorandum 52. (Reprinted IJF 20(1), 2004.) Winters, P. R. (1960). Forecasting sales by exponentially weighted moving averages. *Management Science*, 6(3), 324–342.

Implementation: `packages/dqt/src/dqt/algorithms/timeseries/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_sessions",
    column_name="sessions",
    detector_slug="holt_winters",
    params={'period': 7, 'alpha': 0.99},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Requires regular cadence and a known period.
- Fits a full model on every fit() call; cache when running frequently.

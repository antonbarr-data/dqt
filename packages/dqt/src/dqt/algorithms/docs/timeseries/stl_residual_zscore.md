# STL residual Z-score (`stl_residual_zscore`)

**Group:** `timeseries` · **Kind:** `sample` · **Version:** `1` · **Min N:** 14

## What it computes

Runs `statsmodels.tsa.seasonal.STL` (with `robust=True`) on the reference. Stores residual mean and stddev. At score time decomposes the current window and reports the maximum absolute Z-score of the residuals.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period` | `int` | `7` | Seasonal period in number of observations |

## Assumptions

- Series has a stable seasonal period (default 7 for daily data with weekly seasonality).
- Reference contains ≥ 2 × period observations.
- Residuals are approximately normal (raw count or percentage data may inflate FPR).

## When it works well

- Regular time series with clear seasonal cycles (page views, hourly traffic, daily bookings).
- Spike detection that respects weekly / daily patterns.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Wrong seasonality period | `period` mismatch leaves seasonal signal in residuals | Verify period matches the data cadence (auto-detection in J.1) |
| Non-stationary trend | Fast trend changes appear in residuals | Check `details['trend_magnitude']`; CUSUM may handle abrupt shifts better |
| Too-short series | min_len = 2×period + 1 enforced; raises ValueError below | Ensure series ≥ 2 × period + 1 observations |
| Heavy-tailed residuals | Z-score inflated | Raise the z_threshold or transform |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.3% | Theoretical 0.27% at three-sigma threshold |
| Lognormal | ~1-5% | Right-skew residuals inflate Z-score |
| Poisson | ~0.5-1% | Discrete; mild inflation |
| Beta | ~0.5% | Bounded |
| Pareto | ~5-10% | Heavy tail; raise z_threshold |
| Exponential | ~2-5% | Right-skew residuals |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.3% |
| Lognormal | (default) | ~1-5% |
| Poisson | (default) | ~0.5-1% |
| Beta | (default) | ~0.5% |
| Pareto | (default) | ~5-10% |
| Exponential | (default) | ~2-5% |

## Citation

Cleveland, R. B., Cleveland, W. S., McRae, J. E., & Terpenning, I. (1990). STL: A seasonal-trend decomposition procedure based on Loess. *Journal of Official Statistics*, 6(1), 3–73.

Implementation: `packages/dqt/src/dqt/algorithms/timeseries/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    column_name="booking_count",
    detector_slug="stl_residual_zscore",
    params={'period': 7},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Requires a known seasonal period.
- Residual Z-score inherits the Z-score limitations on heavy-tailed residuals.

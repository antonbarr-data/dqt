# Prophet anomaly (`prophet_anomaly`)

**Group:** `timeseries` · **Kind:** `sample` · **Version:** `1` · **Min N:** 60

## What it computes

Trains Meta's Prophet (requires the optional `dqt[forecast]` extra) on the reference window. Forecasts n steps and counts the fraction of current values outside Prophet's `interval_width` uncertainty band.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `interval_width` | `float` | `0.95` | Width of Prophet's uncertainty interval (e.g. 0.95 = 95% PI) |

## Assumptions

- Series has a regular date index (Prophet expects daily by default).
- Reference contains ≥ 60 days for stable trend + weekly seasonality.
- The `prophet` package is installed.

## When it works well

- Long reference windows (90+ days) with multi-scale seasonality and holidays.
- Daily business KPIs (revenue, bookings) where Prophet's automatic changepoint detection helps.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Missing days in series | Prophet expects a complete daily series; gaps create false anomalies | Reindex to full date range and fill missing values |
| `prophet` not installed | ImportError at fit/score time | Install `dqt[forecast]` |
| Slow fit | Prophet uses Stan/MCMC; 5–30 s per column | Cache fitted model; refit weekly not daily |
| Wide confidence bands on short series | < 30 data points → bands too wide to detect moderate anomalies | Collect ≥ 60 days of history before enabling |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~1% | interval_width=0.99 default |
| Lognormal | ~5-10% | Heavy tail inflates residuals |
| Poisson | ~2-3% | Discrete; mild inflation |
| Beta | ~2-3% | Bounded |
| Pareto | ~10-20% | Heavy tail; do not use without transform |
| Exponential | ~5-10% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~1% |
| Lognormal | (default) | ~5-10% |
| Poisson | (default) | ~2-3% |
| Beta | (default) | ~2-3% |
| Pareto | (default) | ~10-20% |
| Exponential | (default) | ~5-10% |

## Citation

Taylor, S. J. & Letham, B. (2018). Forecasting at scale. *The American Statistician*, 72(1), 37–45.

Implementation: `packages/dqt/src/dqt/algorithms/timeseries/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    column_name="revenue_usd",
    detector_slug="prophet_anomaly",
    params={'interval_width': 0.95},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Requires the optional `dqt[forecast]` extra.
- Computationally heavy at fit time.
- Requires regular date index with no gaps.

# BOCPD (`bocpd`)

**Group:** `timeseries` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Maintains a Bayesian posterior over run lengths via Adams & MacKay's truncated recurrence. Reports `max P(r ≤ 1)` over the current window — the maximum posterior probability of a changepoint.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `hazard_lambda` | `float` | `250.0` | Expected run length between changepoints in observations |

## Assumptions

- Univariate numeric stream.
- Reference window ≥ 100 observations for max_run truncation to be meaningful.
- Observation model is approximately Gaussian (with Student-t predictive for robustness).
- Changepoints are abrupt level shifts, not gradual trends.

## When it works well

- Strategy-level shifts in a metric (pricing policy change, A/B rollout).
- Probabilistic changepoint detection where confidence is needed alongside the alarm.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Short reference window (< 50 rows) | max_run capped too low; long-run hypothesis not established | Use N ≥ 100 |
| kappa0 too tight | Post-change observations equally unlikely under new and old prior | Default kappa0=0.1 is intentionally wide |
| hazard_lambda too small (< 10) | Prior CP probability > 0.10 per step; constant alarms | Default hazard_lambda=250 (~0.4% prior per step) |
| Variance-only change | Mean-preserving scale shift does not move the score | Pair with `stl_residual_zscore` |
| Smooth gradual drift | Score stays low; no run-length hypothesis spikes | Use `adwin` or `page_hinkley` |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~2% | Hazard prior of 1/250 per step |
| Lognormal | ~5-10% | Heavy tail challenges Gaussian likelihood |
| Poisson | ~3% | Discrete; Student-t robustness helps |
| Beta | ~3% | Bounded |
| Pareto | ~10-15% | Heavy tail |
| Exponential | ~5% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~2% |
| Lognormal | (default) | ~5-10% |
| Poisson | (default) | ~3% |
| Beta | (default) | ~3% |
| Pareto | (default) | ~10-15% |
| Exponential | (default) | ~5% |

## Citation

Adams, R. P. & MacKay, D. J. C. (2007). Bayesian online changepoint detection. *arXiv:0710.3742*.

Implementation: `packages/dqt/src/dqt/algorithms/timeseries/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    column_name="median_price_usd",
    detector_slug="bocpd",
    params={'hazard_lambda': 250.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Univariate by design.
- Detects mean shifts; pair with another detector for variance shifts.
- max_run truncation set by reference length; ensure reference is long enough.

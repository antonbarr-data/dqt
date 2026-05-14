# CUSUM (two-sided) (`cusum`)

**Group:** `timeseries` · **Kind:** `sample` · **Version:** `1` · **Min N:** 20

## What it computes

Computes reference mean μ and stddev σ. Runs the two-sided CUSUM recurrence and reports `max(S_hi, -S_lo) / h` — the normalised alarm statistic. Score ≥ 1.0 means the chart has triggered.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `k` | `float` | `0.5` | Allowance in σ units; half the minimum shift to detect |
| `h` | `float` | `50.0` | Decision threshold in σ-accumulated units |

## Assumptions

- Univariate numeric stream.
- Reference is stationary (no trend); detrend or use BOCPD if not.
- Distribution is approximately normal; consider MAD normalisation for heavy tails.

## When it works well

- Detecting persistent mean shifts ahead of single-point detectors.
- Sequential / streaming monitoring with O(1) update per step.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Point spikes that immediately revert | Single large outlier inflates S_hi but chart resets | Use `stl_residual_zscore` or `generalized_esd` |
| Non-stationary reference (trend present) | Cumulative sum drifts continuously | Detrend first or use `bocpd` |
| Heavy-tailed data | σ is a poor spread estimate; CUSUM noisy | Normalise with MAD before feeding to CUSUM |
| Persistent drift not reset | After detection the cumulative sum does not auto-reset | Reset explicitly after acknowledging an incident; or use `adwin` |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.5-2% | Controlled by h parameter |
| Lognormal | ~5-10% | σ a poor spread estimate for heavy tail |
| Poisson | ~2-3% | Discrete; well behaved |
| Beta | ~2% | Bounded |
| Pareto | ~10-15% | Heavy tail |
| Exponential | ~5-7% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.5-2% |
| Lognormal | (default) | ~5-10% |
| Poisson | (default) | ~2-3% |
| Beta | (default) | ~2% |
| Pareto | (default) | ~10-15% |
| Exponential | (default) | ~5-7% |

## Citation

Page, E. S. (1954). Continuous inspection schemes. *Biometrika*, 41(1–2), 100–115.

Implementation: `packages/dqt/src/dqt/algorithms/timeseries/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    column_name="bookings",
    detector_slug="cusum",
    params={'k': 0.5, 'h': 50.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Univariate.
- Reference mean and stddev must be correctly estimated; bad reference produces continuous drift.
- Not designed for variance changes or spikes.

# Matrix Profile (discords) (`matrix_profile`)

**Group:** `timeseries` · **Kind:** `sample` · **Version:** `1` · **Min N:** 30

## What it computes

Computes the self-join Matrix Profile of the reference series (STUMPY if installed, numpy fallback otherwise). Records the 99th percentile of self-distances as threshold. Returns the fraction of current subsequences whose 1-NN distance to reference subsequences exceeds the threshold.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `window` | `int` | `7` | Subsequence length in observations |

## Assumptions

- Series is long enough that subsequences of length `window` are well-defined (≥ 4 × window).
- Subsequence shape carries the anomaly signal, not just level.
- Z-normalisation within subsequences handles local scale; global trend is removed or absent.

## When it works well

- Detecting unusual *shape patterns* (e.g. atypical intra-day session-length profile).
- Time series with repeating motifs where anomalies appear as morphological discords.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Window size sensitivity | Wrong window misses long patterns or is too coarse for short anomalies | Set window to expected anomaly duration in samples |
| Series shorter than 2m+1 samples | Too short to compute the profile | Ensure series length > 2 × window + 1 |
| STUMPY not installed | Falls back to numpy O(n²) | Install `dqt[forecast]` for production use |
| Strong global trend | All current subsequences may be novel due to trend drift | Detrend before scoring |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~2-5% | 99th-percentile threshold from reference |
| Lognormal | ~5-10% | Heavy tail inflates z-normalised distances |
| Poisson | ~3-5% | Discrete; mild inflation |
| Beta | ~3-5% | Bounded |
| Pareto | ~10-15% | Heavy tail |
| Exponential | ~5-8% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~2-5% |
| Lognormal | (default) | ~5-10% |
| Poisson | (default) | ~3-5% |
| Beta | (default) | ~3-5% |
| Pareto | (default) | ~10-15% |
| Exponential | (default) | ~5-8% |

## Citation

Yeh, C.-C. M., Zhu, Y., Ulanova, L., Begum, N., Ding, Y., Dau, H. A., Silva, D. F., Mueen, A., & Keogh, E. (2016). Matrix Profile I. *IEEE ICDM 2016*, 1317–1322.

Implementation: `packages/dqt/src/dqt/algorithms/timeseries/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_sessions",
    column_name="page_views",
    detector_slug="matrix_profile",
    params={'window': 24},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Computational cost — O(n²) numpy fallback; install STUMPY for long series.
- Window length must be chosen domain-appropriately.

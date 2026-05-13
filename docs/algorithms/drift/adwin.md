# ADWIN (`adwin`)

**Group:** `drift` · **Kind:** `sample` · **Version:** `1` · **Min N:** 60

## What it computes

Concatenates reference and current arrays and tests candidate cut-points using Hoeffding's bound. Drift is declared if any sub-window pair shows a mean difference exceeding `sqrt(log(2/delta) / (2m))`. Score is binary 0/1.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `delta` | `float` | `0.002` | Confidence parameter; lower = fewer false alarms, slower detection |

## Assumptions

- The stream is numeric and univariate (operates on the first column).
- The shift of interest is in the mean; ADWIN is not sensitive to variance-only shifts.
- Combined reference + current has at least 60 observations.
- The data is not heavy-tailed; log-transform Pareto/Zipf data before scoring.

## When it works well

- Streaming numeric KPIs where shift timing is unknown and a single binary alarm is acceptable.
- Lightweight production monitoring — no kernel matrices, no neighbour lookups.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Variance-only shift | drift_detected=False when stddev doubles but mean is stable | Pair with `ks_pvalue` or `mmd` for shape changes |
| Short current window (< 30 rows) | drift_detected=False always — minimum window enforced | Collect more data; ADWIN needs ≥ 60 combined rows |
| Heavy-tailed data (Pareto, Zipf) | Extreme values pull sub-window means past the Hoeffding bound | Log-transform or switch to `wasserstein_1` |
| Identical distribution sub-cuts | False alarms on reference-vs-itself due to unequal sub-window comparisons | Increase `delta` (e.g. 0.001) or use a smaller `min_window` |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.5% | Hoeffding bound on identical distributions |
| Lognormal | ~3-8% | Heavy tail inflates sub-window mean variance |
| Poisson | ~1% | Discrete; mild tail |
| Beta | ~1% | Bounded; well behaved |
| Pareto | ~10-15% | Very heavy tail; FPR elevated |
| Exponential | ~3-5% | Right-skew inflates sub-window mean variance |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.5% |
| Lognormal | (default) | ~3-8% |
| Poisson | (default) | ~1% |
| Beta | (default) | ~1% |
| Pareto | (default) | ~10-15% |
| Exponential | (default) | ~3-5% |

## Citation

Bifet, A. & Gavalda, R. (2007). *Learning from Time-Changing Data with Adaptive Windowing*. Proceedings of SIAM SDM, 443–448.

Implementation: `packages/dqt/src/dqt/algorithms/drift/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    column_name="bookings_per_day",
    detector_slug="adwin",
    params={'delta': 0.002},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Univariate by design; run one instance per column for multi-column drift.
- Score is binary; pair with `wasserstein_1` for magnitude.
- FPR elevated on heavy-tailed data without log transform.

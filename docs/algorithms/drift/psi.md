# Population Stability Index (`psi`)

**Group:** `drift` · **Kind:** `sample` · **Version:** `1` · **Min N:** 200

## What it computes

Bins reference into `n_bins` equal-width buckets with smoothing, then computes PSI = sum (cur% - ref%) × ln(cur% / ref%). Industry-standard drift score in credit-risk modelling.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `10` | Number of equal-width bins |

## Assumptions

- The column is continuous numeric.
- Sample size ≥ 200 per window for stable bin counts.
- Reference window defines the bins; out-of-range mass goes to edge bins.

## When it works well

- Model scoring pipelines where PSI is already the accepted metric.
- Numeric feature drift in production ML systems with a stable reference.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Zero-count bins | PSI undefined when a bin is empty; smoothing inflates PSI on sparse data | Use ≥ 100 rows per distribution |
| Sparse data (N < 100) | Bin estimates noisy; PSI unstable | Increase sample size |
| Numeric binning sensitivity | Default 10 equal-width bins may be wrong for bimodal data | Set `n_bins` manually; for ordinal use `chi_square_drift` |
| Dataset-agnostic thresholds | 0.1/0.2 thresholds were developed for credit scoring; may not suit all domains | Calibrate via `calibrate_from_history()` |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5-10% | Industry-standard thresholds |
| Lognormal | ~10-20% | Heavy tail inflates PSI |
| Poisson | ~6% | Discrete; moderate bin sparsity |
| Beta | ~5% | Bounded |
| Pareto | ~15-25% | Heavy tail; widen bands |
| Exponential | ~10-15% | Right-skew; moderate elevation |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5-10% |
| Lognormal | (default) | ~10-20% |
| Poisson | (default) | ~6% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~15-25% |
| Exponential | (default) | ~10-15% |

## Citation

PSI is an industry standard originating in credit-risk model validation; widely documented in OCC SR 11-7 model risk guidance. No single canonical paper.

Implementation: `packages/dqt/src/dqt/algorithms/drift/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    column_name="amount_paid_usd",
    detector_slug="psi",
    params={'n_bins': 10},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Sensitive to bin count and zero-mass bins.
- Asymmetric in bin definition: reference defines the bins.

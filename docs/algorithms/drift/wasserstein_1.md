# Wasserstein-1 (normalised) (`wasserstein_1`)

**Group:** `drift` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Computes `scipy.stats.wasserstein_distance` between reference and current arrays, normalised by the reference standard deviation. Reports drift magnitude in sigma units.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- The column is continuous numeric.
- Reference standard deviation is non-zero and representative.
- Sample size ≥ 100 per window; ≥ 500 for the default warn threshold to be reliable.

## When it works well

- Continuous columns where the *magnitude* of drift matters, not just statistical significance.
- Heavy-tailed columns where distribution-free measures are preferred (no normality assumption).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Small N (< 200) | False alarms on identical distributions | Collect more data; use `ks_pvalue` for small samples |
| Heavy-tailed reference distribution | Stddev inflated; normalised score deflated | Use raw `details['raw_distance']` or log-transform |
| Categorical columns | Earth-mover distance on integer encodings has no probabilistic interpretation | Use `chi_square_drift` for categorical |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~1-3% | Sampling variance of normalised W1 |
| Lognormal | ~5-10% | Stddev inflated by tail; score noisy |
| Poisson | ~2% | Discrete; W1 depends on quantisation |
| Beta | ~2% | Bounded; well behaved |
| Pareto | ~5-10% | Heavy tail; stddev unstable |
| Exponential | ~3-5% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~1-3% |
| Lognormal | (default) | ~5-10% |
| Poisson | (default) | ~2% |
| Beta | (default) | ~2% |
| Pareto | (default) | ~5-10% |
| Exponential | (default) | ~3-5% |

## Citation

Kantorovich, L. V. (1942). *On the translocation of masses*. Doklady Akademii Nauk SSSR, 37(7–8), 227–229.

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
    detector_slug="wasserstein_1",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Normalisation can be unstable for near-constant reference columns.
- Reports magnitude in sigma units; raw distance available in details.

# KL divergence (`kl_divergence`)

**Group:** `drift` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Bins reference into `n_bins` equal-width bins with smoothing, then computes `KL(current ‖ reference) = sum cur_p × log(cur_p / ref_p)` against the current window. Asymmetric; sensitive to new modes in the current window.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `10` | Number of equal-width bins for discretising the distributions |

## Assumptions

- The column is continuous numeric.
- Sample size ≥ 100 per window.
- Reference distribution covers the support of the current distribution (otherwise smoothing inflates the score).

## When it works well

- Information-theoretic drift summaries in pipeline-level KPIs.
- Detecting new modes appearing in the current window (KL is asymmetric).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Zero-probability bins | KL is undefined when P=0 and Q>0 | Smoothing applied; very sparse data still gives unstable scores |
| Asymmetry | KL(P||Q) != KL(Q||P) | Use `js_divergence` for a symmetric version |
| Unbounded | Can go to infinity for disjoint distributions | Check `details['score_raw']`; or use `js_divergence` |
| Not a metric | Violates triangle inequality; can't compare across columns | Use `wasserstein_1` for column-to-column comparisons |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5-10% | Smoothing handles zero-mass bins; mild inflation |
| Lognormal | ~10-15% | Heavy tail inflates score on bin sparsity |
| Poisson | ~6% | Discrete; sparse bins |
| Beta | ~5-8% | Bounded; well behaved |
| Pareto | ~15-25% | Very heavy tail; score elevated |
| Exponential | ~8-12% | Right-skew; moderate elevation |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5-10% |
| Lognormal | (default) | ~10-15% |
| Poisson | (default) | ~6% |
| Beta | (default) | ~5-8% |
| Pareto | (default) | ~15-25% |
| Exponential | (default) | ~8-12% |

## Citation

Kullback, S. & Leibler, R. A. (1951). On information and sufficiency. *Annals of Mathematical Statistics*, 22(1), 79–86.

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
    detector_slug="kl_divergence",
    params={'n_bins': 10},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Asymmetric and unbounded.
- Sensitive to bin count and zero-mass regions.

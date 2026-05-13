# Jensen-Shannon distance (`js_divergence`)

**Group:** `drift` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Bins reference into `n_bins` equal-width bins, applies smoothing, and calls `scipy.spatial.distance.jensenshannon` against the current window. Returns the JS *distance* (square root of JS divergence) in `[0, 1]`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `10` | Number of equal-width bins for discretising the distributions |

## Assumptions

- The column is continuous numeric (categorical → use `chi_square_drift`).
- Sample size ≥ 100 per window for stable bin counts.
- Smoothing handles zero-count bins gracefully but does not remove their effect at very small N.

## When it works well

- Bounded, interpretable drift score comparable across columns of different scale.
- Primary drift metric for dashboard overviews.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Zero-count bins | Smoothing applied but score still sensitive to sparse bins | Require ≥ 50 rows per window |
| Bounded range | Both JS and KL saturate at extreme drift | Pair with `wasserstein_1` for unbounded magnitude |
| Categorical data | Requires discrete or binned distributions | Use `chi_square_drift` instead |

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

Lin, J. (1991). Divergence measures based on the Shannon entropy. *IEEE Transactions on Information Theory*, 37(1), 145–151.

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
    detector_slug="js_divergence",
    params={'n_bins': 10},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Requires binning; sensitive to bin count.
- Bounded [0, 1] — saturates on very large shifts.

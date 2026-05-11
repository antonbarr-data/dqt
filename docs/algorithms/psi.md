# `drift.psi`

> *Population Stability Index* — measures how much a numeric distribution has shifted relative to a reference by binning both windows and computing the weighted symmetric divergence; the industry-standard drift score from credit-risk modelling.

## What it does

At fit time, bins the reference column into `n_bins` equal-width buckets (using numpy's histogram bin edges) and stores the fractional count per bin with Laplace smoothing (ε = 1e-6). At score time it bins the current window using the same edges, computes PSI = Σ (cur% − ref%) × ln(cur% / ref%), and returns the result. The formula is symmetric in the log-ratio sense and equals zero when the two distributions are identical. By convention: PSI < 0.1 = stable, 0.1–0.2 = moderate shift, > 0.2 = significant population shift.

## When to use it

- Model scoring pipelines where PSI is already the accepted metric — results are directly comparable to existing monitoring baselines.
- Numeric feature drift in production ML systems.
- When you need an interpretable, single-number drift summary that non-statisticians understand.
- Suitable for moderate to large samples (≥ 200 rows per window) to get stable bin counts.

## When not to use it

- Categorical columns — use `chi_square_drift` or `cramers_v`; PSI requires numeric binning.
- Very small samples — sparse bins inflated by the ε smoothing can produce misleading scores.
- When you need a calibrated p-value or hypothesis test — PSI has no distributional null hypothesis; use `ks_pvalue` instead.
- Long-tailed distributions where most mass is in a few bins — bin edges computed on the reference may cluster poorly; consider `wasserstein_1` as a complement.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `10` | Number of equal-width bins used to discretise the reference distribution |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.10` |
| `fail_threshold` | `0.20` |
| `direction` | `lower_is_better` |
| `score meaning` | PSI value; < 0.1 stable, 0.1–0.2 moderate shift, > 0.2 significant population shift |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.psi import PSIDetector

rng = np.random.default_rng(42)
# fct_bookings.amount_paid_usd — credit-risk-style stability check on booking amounts
ref = pd.DataFrame({"amount_paid_usd": rng.normal(80, 20, 2000)})
curr_drift = pd.DataFrame({"amount_paid_usd": rng.normal(100, 20, 2000)})  # shifted mean

det = PSIDetector(
    n_bins=10,  # bins to discretise both reference and current distributions;
                # 10 is standard for PSI in financial risk;
                # increase to 20 for high-cardinality continuous columns;
                # decrease to 5 for narrow-range or sparse columns
)
state = det.fit(ref)
result = det.score(curr_drift, state)
print(result.verdict)        # warn or fail
print(result.plain_english)  # "PSI = 0.2347 — significant population shift"
print(result.score)          # ~0.23
```

## Learn more

- 📺 [Population Stability Index (PSI) for Scorecards | Monitor Model Drift in Python](https://www.youtube.com/watch?v=iWJcITAge-c) — shows how PSI is calculated bin-by-bin, explains the 0.1 / 0.2 thresholds, and demonstrates PSI monitoring in Python.

## Implementation

[`packages/dqt/src/dqt/algorithms/drift/psi.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/drift/psi.py)

## Reference

- PSI is an industry standard originating in credit-risk model validation; no single canonical paper. Widely documented in OCC model risk management guidance (SR 11-7).
- `packages/dqt/src/dqt/algorithms/drift/psi.py`

## Tests

`packages/dqt/tests/algorithms/drift/test_psi.py`

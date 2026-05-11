# `info.cramers_v`

> *Cramér's V (drift)* — measures the strength of categorical drift by building a 2 × K contingency table (reference vs. current) and reporting Cramér's V as a normalised association coefficient; score ∈ [0, 1].

## What it does

At fit time, records the value counts of the reference column. At score time it constructs a 2 × K contingency table (one row for reference counts, one for current counts across all K reference categories), runs `scipy.stats.chi2_contingency` to obtain χ², and computes V = √(χ² / (n × (min(rows, cols) − 1))). With 2 rows, min(rows, cols) − 1 = 1, so V = √(χ² / n). The result is clamped to [0, 1]: 0 means the relative frequency distributions are identical, 1 means they are maximally different. Unlike `chi_square_drift`, V is an effect-size measure rather than a test statistic, making it comparable across columns with different numbers of categories and different sample sizes.

## When to use it

- Categorical columns where you want a normalised drift *magnitude* rather than a p-value.
- Comparing drift intensity across multiple categorical columns on a common [0, 1] scale.
- Summarising categorical drift in dashboard KPIs or stat gauge banks.
- When `chi_square_drift` signals drift but you want to quantify how severe it is.

## When not to use it

- When a p-value is the required output — use `chi_square_drift` instead.
- Numeric continuous columns — use `ks_pvalue`, `wasserstein_1`, or `psi`.
- Very small windows (< 30 per category) — chi² approximation is unreliable and V is noisy.
- Binary columns with highly imbalanced classes — V can be inflated; interpret alongside absolute count differences.

## Parameters

This detector has no constructor parameters.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | — |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.15` |
| `fail_threshold` | `0.30` |
| `direction` | `lower_is_better` |
| `score meaning` | Cramér's V ∈ [0, 1]; 0 = no drift, 0.15 = moderate drift, 0.3+ = strong drift |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.info.cramers_v import CramersVDetector

rng = np.random.default_rng(42)
# reference: roughly balanced across 4 categories
ref_cats = rng.choice(["A", "B", "C", "D"], size=2000, p=[0.25, 0.25, 0.25, 0.25])
ref = pd.DataFrame({"category": ref_cats})

# current: D collapses, A takes its share
curr_cats = rng.choice(["A", "B", "C", "D"], size=2000, p=[0.50, 0.25, 0.20, 0.05])
curr_drift = pd.DataFrame({"category": curr_cats})

det = CramersVDetector()
state = det.fit(ref)
result = det.score(curr_drift, state)
print(result.verdict)        # warn or fail
print(result.plain_english)  # "Cramér's V = 0.2341 — categorical drift"
print(result.score)          # ~0.23

# stable window — same distribution as reference
curr_stable = pd.DataFrame({
    "category": rng.choice(["A", "B", "C", "D"], 2000, p=[0.25, 0.25, 0.25, 0.25])
})
print(det.score(curr_stable, state).verdict)  # pass
```

## Reference

- Cramér, H. (1946). *Mathematical Methods of Statistics*. Princeton University Press. (§21.6)
- `packages/dqt/src/dqt/algorithms/info/cramers_v.py`

## Tests

`packages/dqt/tests/algorithms/info/test_cramers_v.py`

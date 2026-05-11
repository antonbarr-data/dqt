# `drift.wasserstein_1`

> *Wasserstein-1 (norm.)* — measures the total mass transport cost between reference and current distributions, normalised by the reference standard deviation to give a dimensionless shift in units of σ.

## What it does

Stores the reference column values and their standard deviation at fit time. At score time it computes `scipy.stats.wasserstein_distance` (the 1-Wasserstein / earth-mover distance) between the two empirical distributions and divides by the reference std, yielding a scale-invariant score. A score of 0.20 corresponds roughly to a 0.2σ shift in the distribution's centre of mass — the warn threshold. A score of 0.50 (half a standard deviation) is the fail threshold. Unlike KS, Wasserstein accounts for *how far* mass moved, not just whether the CDFs differ, making it sensitive to both location shifts and shape changes proportional to their magnitude.

## When to use it

- Continuous numeric columns where the *magnitude* of drift matters, not just its statistical significance.
- Metric time-series checks where a small but persistent shift deserves a proportionate signal (e.g. revenue, latency).
- Complement to `ks_pvalue`: KS detects any CDF difference; Wasserstein quantifies how large the shift is.
- When sample sizes are small-to-moderate and you want a more stable score than p-value-based tests.
- When distributions are heavy-tailed or skewed — Wasserstein does not assume normality.

## When not to use it

- Categorical columns — use `chi_square_drift` or `cramers_v`.
- When the reference std is near zero (constant columns) — the normalisation becomes unstable; the implementation clamps to ε = 1e-8 but the score will be very large for any shift.
- When drift magnitude in physical units (not σ) is required — use the raw `details["raw_distance"]` instead.

## Parameters

This detector has no constructor parameters.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | — |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.20` |
| `fail_threshold` | `0.50` |
| `direction` | `lower_is_better` |
| `score meaning` | Earth-mover distance divided by reference std; 0.2 = moderate shift (~0.2σ), 0.5 = large shift |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

rng = np.random.default_rng(42)
ref = pd.DataFrame({"value": rng.normal(100, 10, 1000)})
curr_drift = pd.DataFrame({"value": rng.normal(115, 10, 1000)})  # 1.5σ mean shift

det = Wasserstein1Detector()
state = det.fit(ref)
result = det.score(curr_drift, state)
print(result.verdict)        # fail (1.5σ >> 0.5 threshold)
print(result.plain_english)  # "Wasserstein-1 distance = 15.0 (1.50σ of reference); drift detected"
print(result.score)          # ~1.5
print(result.details["raw_distance"])  # ~15.0 (in original units)
```

## Reference

- Kantorovich, L. V. (1942). On the translocation of masses. *Doklady Akademii Nauk SSSR*, 37(7–8), 227–229.
- Wasserstein, L. N. (1969). Markov processes over denumerable products of spaces describing large systems of automata. *Problemy Peredachi Informatsii*, 5(3), 47–52.
- `packages/dqt/src/dqt/algorithms/drift/wasserstein.py`

## Tests

`packages/dqt/tests/algorithms/drift/test_wasserstein_1.py`

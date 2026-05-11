# `info.mutual_information`

> *Mutual information (norm.)* — quantifies distributional similarity between a reference window and a current window using Normalized Mutual Information over a joint histogram; higher score means more similar distributions.

## What it does

At fit time the detector records the reference array (first column of the input DataFrame) and computes equal-width histogram bin edges with `n_bins` bins. At score time it builds a joint 2D histogram between the reference and current arrays using those same bin edges, normalises it to a probability matrix, and computes:

```
NMI = MI(ref, curr) / √(H(ref) × H(curr))
```

where `MI = H(ref) + H(curr) − H(joint)` and `H` is Shannon entropy. The result is bounded `[0, 1]`: `1.0` = identical distributions, lower values indicate increasing divergence. Note the direction is `higher_is_better` — the score *falls* as drift increases.

## When to use it

- When you want an information-theoretic measure of similarity that is symmetric and bounded, as opposed to asymmetric measures like KL divergence.
- Detecting changes in the shape of a distribution (not just the mean) without assuming any particular parametric form.
- Useful as a complement to `wasserstein_1` (which emphasises magnitude) when you care equally about shape changes.
- Quantifying how much information one variable (e.g. `dim_sellers.tier`) shares with an outcome (e.g. `converted`) — NMI = 0 means statistical independence.

## When not to use it

- Very small samples (< 100 rows per window) — histogram-based NMI is sensitive to bin edge placement and can produce noisy estimates; prefer `ks_pvalue` for small samples.
- Categorical columns with high cardinality — many bins will be sparse; use `chi_square_drift` or `cramers_v` for categorical variables.
- When you need a hypothesis test p-value — NMI is a similarity score, not a test statistic with an analytic null distribution.
- When the score direction (`higher_is_better`) conflicts with downstream alerting logic expecting `lower_is_better`; note the warn threshold is `0.50` (warn when NMI < 0.50).

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `20` | Number of equal-width histogram bins. Computed from the reference range at fit time; the same edges are reused at score time. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.50` |
| `fail_threshold` | `0.30` |
| `direction` | `higher_is_better` |
| `score meaning` | Normalized MI between reference and current periods; `1.0` = identical, lower = more drift; warn when NMI < 0.50, fail when NMI < 0.30 |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.info.mutual_information import MutualInformationDetector

rng = np.random.default_rng(42)
n = 2000

# Gigler dim_sellers: tier (encoded 0=bronze, 1=silver, 2=gold) and conversion flag
# Here we use tier as a numeric proxy for the NMI calculation
ref_tier = pd.DataFrame({"tier": rng.choice([0, 1, 2], size=n, p=[0.5, 0.3, 0.2])})

# Current period: same distribution — tier mix unchanged
curr_same = pd.DataFrame({"tier": rng.choice([0, 1, 2], size=500, p=[0.5, 0.3, 0.2])})
# Current period: tier mix shifted (many more gold sellers)
curr_shift = pd.DataFrame({"tier": rng.choice([0, 1, 2], size=500, p=[0.1, 0.2, 0.7])})

det = MutualInformationDetector(n_bins=3)   # 3 bins = 3 tiers
state = det.fit(ref_tier)

result_same = det.score(curr_same, state)
print(result_same.verdict)   # pass
print(result_same.score)     # high, e.g. ~0.95

result_shift = det.score(curr_shift, state)
print(result_shift.verdict)        # fail
print(result_shift.plain_english)  # "Normalized MI = 0.1832 — drift detected"
```

## Learn more

- 📺 [Mutual Information, Clearly Explained!!! — StatQuest with Josh Starmer](https://www.youtube.com/watch?v=eJIp_mgVLwE) — builds mutual information from entropy fundamentals with clear bar-chart visualisations.

## Reference

- Cover, T.M. & Thomas, J.A. (2006). *Elements of Information Theory* (2nd ed.). Wiley-Interscience.
- `packages/dqt/src/dqt/algorithms/info/mutual_information.py`

## Tests

`packages/dqt/tests/algorithms/info/test_mutual_information.py`

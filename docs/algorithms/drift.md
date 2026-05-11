# Drift Detectors

## Wasserstein-1 / Earth-Mover Distance (`wasserstein_1`)
**Ref:** Kantorovich (1942); Rubner et al. (2000) *IJCV*

Measures the minimum "work" to transform one distribution into another. Score is normalized by reference std so it's interpretable across scales.

**Assumptions:** Continuous or ordinal data. No distributional assumptions.

**Works well when:** Gradual shifts, heavy-tailed distributions, revenue/count/ratio data. The recommended default for numeric drift. Sensitive to both location and shape changes.

**Fails when:** Data is categorical (use chi-square or PSI). Very small N (<100) produces high variance.

**Thresholds:** score 0.2 = moderate shift (~0.2 std); score 0.5 = large shift (~0.5 std).

**Minimum N:** 500 recommended for stable estimates.

```python
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
det = Wasserstein1Detector()
# Returns normalized earth-mover distance
```

## Two-Sample KS Test (`ks_pvalue`)
**Ref:** Kolmogorov (1933); Smirnov (1948)

Tests whether two samples come from the same distribution using the supremum of CDF differences.

**Assumptions:** Continuous data. IID samples.

**Works well when:** You want a p-value for "are these distributions the same?" Sharp detection of shape changes.

**Fails when:** Very large N — at N=10k, KS flags negligible differences as significant. Discrete or categorical data (use chi-square). For gradual drift prefer Wasserstein-1.

**Note:** Score = 1 − p-value. Large samples will nearly always produce significant results even when the actual shift is negligible. Use `n_ref` and `n_curr` in details to assess power.

```python
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
det = KS2SampleDetector()
```

## PSI (`psi`)
**Ref:** Industry standard (insurance/credit scoring), no single canonical paper

Bins the reference distribution, counts current distribution in same bins. PSI < 0.1: stable. 0.1–0.2: moderate shift. > 0.2: significant population shift.

**Assumptions:** Requires sufficient data per bin (≥5 per bin recommended). Works on numeric and categorical data.

**Works well when:** Monitoring model input features for population shift. Industry-standard interpretability.

**Fails when:** Continuous data with non-standard distributions — bin edges from reference may misrepresent the current distribution. Use Wasserstein-1 for continuous data.

```python
from dqt.algorithms.drift.psi import PSIDetector
det = PSIDetector(n_bins=10)
```

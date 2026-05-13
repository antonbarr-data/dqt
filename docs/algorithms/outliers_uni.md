# Univariate Outlier Detectors

## IQR Fence (`iqr_fence`)
**Ref:** Tukey (1977) *Exploratory Data Analysis*

Flags values outside Q1 − k·IQR and Q3 + k·IQR. Default k=3.0 (outer fence).

**Assumptions:** No normality required. Works on any unimodal distribution.

**Works well when:** Data is roughly symmetric. Sample N ≥ 50.

**Fails when:** Extremely heavy-tailed distributions (Pareto, Zipf) — even k=3 may over-flag. Use `adjusted_boxplot` (medcouple correction) instead.

**Expected false-alarm rate at k=3.0:** ~0.0002% on normal data. On log-normal data with σ≥2: ~0.5%.

**Recommended thresholds by data shape:**
- Revenue/order-value (log-normal): use k=3.0 (default)
- Count data (Poisson): use k=1.5 with `warn_threshold=0.001`
- Ratio data (0–1): use k=2.0

```python
from dqt.algorithms.outliers_uni.iqr_fence import IQRFenceDetector
det = IQRFenceDetector(k=3.0)  # outer fence; k=1.5 for inner
```

## Modified Z-Score / MAD (`mad_outlier_fraction`)
**Ref:** Iglewicz & Hoaglin (1993) *How to Detect and Handle Outliers*

Flags values where |0.6745 * (x − median) / MAD| > threshold. Robust to outliers in reference because MAD ignores extreme values when computing scale.

**Default threshold: 11.0** — calibrated for lognormal(0,1) revenue/order data.
The canonical Iglewicz & Hoaglin threshold of 3.5 targets near-Gaussian data and
over-flags heavy-tailed distributions by ~30×.

FPR at default threshold=11.0 by data shape (empirical, N=5000):

| Data shape | Empirical FPR |
|---|---|
| lognormal(0,1) — revenue | 1.060% |
| normal(0,1) — Gaussian | 0.000% |
| poisson(λ=10) — count | 0.000% |
| beta(0.5,0.5) — ratio/score | 0.000% |
| pareto(1.5) — heavy-tail | 3.520% |
| exponential(λ=1) — time between events | 0.020% |

**Assumptions:** Approximately unimodal distribution.

**Works well when:** Data has outliers that would inflate the standard deviation (making Z-score blind). Minimum N=15.

**Fails when:** Multimodal data (bimodal revenue by customer tier). Use a mixture model or `isolation_forest` instead.

**Expected false-alarm rate at threshold 6.5:** ~0.1% on log-normal data; ~0% on near-Gaussian data (conservative — recalibrate for Gaussian if you need high sensitivity).

**Recalibration for your data shape:**
```python
from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
from dqt.algorithms._calibration import suggest_threshold
import numpy as np, pandas as pd

ref = pd.DataFrame({"revenue": your_reference_column})
result = suggest_threshold(MADOutlierDetector(), ref, target_fpr=0.001)
det = MADOutlierDetector(threshold=result["suggested_threshold"])
```

```python
from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
det = MADOutlierDetector()            # default 11.0 — good for revenue/count/heavy-tailed
det_gaussian = MADOutlierDetector(threshold=3.5)   # original — good for near-Gaussian
```

## Grubbs' Test (`grubbs`)
**Ref:** Grubbs (1950) *Ann. Math. Statist.*

Tests whether the single most extreme value is a statistically significant outlier (using the t-distribution).

**Assumptions:** Approximate normality. Tests exactly ONE outlier at a time.

**Works well when:** You expect at most one outlier and data is roughly normal. Classic use: measurement instrument calibration.

**Fails when:** Multiple outliers (masking effect — outliers hide each other). Use GESD instead.

**Minimum N:** 25 for reliable power.

```python
from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
det = GrubbsDetector()
```

## Generalized ESD (`generalized_esd`)
**Ref:** Rosner (1983) *Technometrics* — Percentage Points for a Generalized ESD Many-Outlier Procedure

Tests for up to k outliers simultaneously, handling the masking problem.

**Assumptions:** Approximate normality. N ≥ 50.

**Works well when:** You suspect multiple outliers and data is approximately normal.

**Fails when:** Heavily skewed data (use MAD or IQR instead). Large N (>10k) with only 1–2 real outliers — GESD's fraction score becomes very small.

```python
from dqt.algorithms.outliers_uni.grubbs import GeneralizedESDDetector
det = GeneralizedESDDetector(max_outliers=0, alpha=0.05)  # 0 = auto (max 100)
```

## Failure modes and known limits

This section covers cross-cutting failure modes that apply to all univariate outlier detectors. For detector-specific details see the individual docs (`iqr_fence.md`, `mad_outlier_fraction.md`, `grubbs.md`, `generalized_esd.md`, `zscore_outlier_fraction.md`, `double_mad_outlier_fraction.md`, `adjusted_boxplot_fraction.md`).

All univariate outlier detectors share the assumption of approximately unimodal data. When that assumption fails, every detector here will either over-flag (multimodal) or under-flag (contaminated reference).

| Failure mode | Symptom | Fix |
|---|---|---|
| Multimodal reference data (e.g. B2B vs B2C mixed) | Threshold calibrated on mixture; neither mode is properly flagged | Segment by a grouping dimension; run one detector per segment |
| Contaminated reference (outliers in reference window) | Outliers inflate reference scale (stddev, IQR); future outliers are missed | Clean the reference window; use robust estimators (MAD, adjusted boxplot) |
| Concept drift (distribution shifts over time) | Outlier rate rises gradually; reference becomes stale | Re-fit baselines on a rolling window; trigger re-fit when `ks_pvalue` detects drift |
| Fraction vs. single-point semantics | Fraction-based detectors (mad_outlier_fraction) report the rate of outliers; Grubbs/GESD test for individual points | Use fraction-based detectors for monitoring; use Grubbs/GESD for batch inspection |
| Threshold confusion across detectors | Different detectors use different scales (MAD units, sigma, IQR multiples) - thresholds are not interchangeable | Always use the STAT_SCALES defaults for each detector; do not copy a threshold from one detector to another |

### Detector selection guide

| Data shape | Recommended detector | Avoid |
|---|---|---|
| Approximately normal | `zscore_outlier_fraction` or `grubbs` | MAD (overkill for Gaussian) |
| Heavy-tailed (revenue, latency) | `mad_outlier_fraction` or `adjusted_boxplot_fraction` | Z-score (will miss outliers) |
| Count data (non-negative integers) | `iqr_fence` | Z-score, Grubbs |
| Ratio/score data (0-1) | `iqr_fence` or `adjusted_boxplot_fraction` | Z-score |
| Suspected multiple outliers | `generalized_esd` | Grubbs (masks beyond 1) |
| Unknown distribution | `mad_outlier_fraction` (default) or `auto_outlier` | None |

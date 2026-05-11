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

Flags values where |0.6745 * (x − median) / MAD| > 3.5. Robust to outliers in reference because MAD ignores extreme values when computing scale.

**Assumptions:** Approximately unimodal distribution.

**Works well when:** Data has outliers that would inflate the standard deviation (making Z-score blind). Minimum N=15.

**Fails when:** Multimodal data (bimodal revenue by customer tier). Use a mixture model or `isolation_forest` instead.

**Expected false-alarm rate at threshold 3.5:** ~0.007% on normal data.

```python
from dqt.algorithms.outliers_uni.mad import MADDetector
det = MADDetector(threshold=3.5)  # 3.5 is Iglewicz & Hoaglin's recommendation
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

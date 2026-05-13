# Statistical Primer for dqt

A concise guide to the statistical concepts behind dqt's detectors. Written for
data engineers who know SQL well but may not have a statistics background.

---

## How detectors work

Every detector implements the same two-phase contract:

1. **`fit(reference_df)`** — learn what "normal" looks like from a clean reference window
   (default: last 14 days). Returns a `state` object.
2. **`score(current_df, state)`** — compare the current batch to the reference and return
   a `score` in `[0, 1]`, a `verdict` (pass / warn / fail), and a `plain_english` explanation.

A score of **0.0** means "identical to the reference". A score of **1.0** means maximum
divergence detected. Whether that is bad depends on the detector family.

The `verdict` is derived from `STAT_SCALES` — a single source of truth that maps each
detector's slug to `(warn_threshold, fail_threshold, direction)`. You can override
per-check thresholds with `warn_threshold:` / `fail_threshold:` in the check YAML.

---

## Detector families

### 1. Basic / completeness

These are deterministic rule checks. They do not require a reference window.

- **`completeness`** — fraction of non-null values. Score = null fraction. Fails if > 5%.
- **`uniqueness`** — fraction of distinct values relative to total. Fails if < 80%.
- **`schema_change`** — compares column names and types. Score = 1.0 if any change detected.
- **`referential_integrity`** — checks that FK values exist in the parent table.
- **`freshness_seconds_behind`** — seconds since the most recent row timestamp.

**When to use:** Always. These catch simple operational failures (dropped columns, stalled
pipelines, FK mismatches) before they need statistical analysis.

---

### 2. Outlier detection (univariate)

These detectors ask: "Is the fraction of outlier points higher than in the reference?"
They operate on a single column and return the fraction of rows classified as anomalous.

**Recommended: `auto_outlier` (F1 0.926) — ensemble of IQR + MAD, zero config needed.**

| Detector | Method | Good for |
|---|---|---|
| `mad_outlier_fraction` | Median Absolute Deviation; robust to skew | Heavy-tailed or skewed data |
| `double_mad_outlier_fraction` | Asymmetric MAD; separate thresholds left/right | Strongly skewed distributions |
| `adjusted_boxplot_fraction` | Medcouple-adjusted Tukey fences | Skewed with asymmetric tails |
| `zscore_outlier_fraction` | Classic Z-score; assumes Gaussian | Only valid for roughly normal data |
| `iqr_fence` | Tukey 1.5xIQR fence | Symmetric distributions |
| `isolation_forest_fraction` | Random-tree isolation | High-dimensional; works without normality |

**Common pitfall:** `zscore_outlier_fraction` is statistically invalid on heavy-tailed
(e.g. revenue, transaction amount) distributions. Use `mad_outlier_fraction` or
`adjusted_boxplot_fraction` instead.

**Degenerate distribution guard:** The runner automatically skips outlier scoring when
> 90% of values are null or < 5 unique non-null values exist. The result is tagged
`degenerate_distribution_detected` with verdict `warn`.

---

### 3. Distribution drift

These detectors compare the full shape of the current distribution to the reference.
They catch mean shifts, variance changes, and shape changes simultaneously.

**Recommended: `ks_pvalue` (F1 0.920) for general use; `wasserstein_1` for ordinal/continuous data.**

| Detector | Method | Score interpretation |
|---|---|---|
| `ks_pvalue` | Kolmogorov-Smirnov two-sample test | 1 - p-value; high = likely drifted |
| `psi` | Population Stability Index; bins-based | PSI > 0.25 = significant drift |
| `wasserstein_1` | Earth Mover's Distance (Wasserstein-1) | Average amount data must move to match reference |
| `js_divergence` | Jensen-Shannon divergence | Symmetric KL; bounded in [0, 1] |
| `kl_divergence` | Kullback-Leibler divergence | Asymmetric; sensitive to zero-probability bins |
| `mmd` | Maximum Mean Discrepancy | Kernel-based; works on any distribution |

**When KS fails:** KS assumes continuous distributions. For categorical columns use
`chi_square_drift`. For heavy-tailed data where small shifts in the extreme tail matter,
`wasserstein_1` is more sensitive than KS.

**PSI interpretation guide:**

| PSI | Signal |
|---|---|
| < 0.10 | No significant drift |
| 0.10 – 0.25 | Minor drift, worth monitoring |
| > 0.25 | Significant drift, investigate |

---

### 4. Time-series

These detectors expect an ordered time series and look for anomalies in the temporal
structure — spikes, trend breaks, and seasonal deviations.

| Detector | Method | Best for |
|---|---|---|
| `holt_winters` (F1 0.933) | Triple exponential smoothing; captures level+trend+seasonality | Strongly seasonal metrics (weekly patterns) |
| `stl_residual_zscore` | STL decomposition residual Z-score | Any periodic time series |
| `cusum` (F1 0.884) | Cumulative sum control chart | Persistent mean shifts (not spikes) |
| `bocpd` | Bayesian Online Changepoint Detection | Sudden distribution changes; no seasonality assumption |

**Common pitfall:** Applying `holt_winters` to non-seasonal data produces unreliable
results. Use `stl_residual_zscore` with `period=1` for non-seasonal series, or `cusum`
for detecting sustained level shifts.

---

### 5. Multivariate / information-theoretic

These compare relationships between columns, not just individual distributions.

| Detector | Method | Use case |
|---|---|---|
| `cramers_v` | Cramér's V association | Two categorical columns drifting together |
| `mutual_information` | Shannon MI | Non-linear association between any two columns |
| `mahalanobis_fraction` | Mahalanobis distance | Multivariate outliers accounting for column correlation |

---

## Choosing the right detector

```
Is the column a timestamp or event log?
  → freshness_seconds_behind, date_part_missing_fraction

Is the problem "are nulls increasing"?
  → completeness

Is the problem "are values drifting away from historical norms"?
  Continuous numeric column?
    Strong seasonality? → holt_winters or stl_residual_zscore
    No seasonality?     → ks_pvalue or wasserstein_1
  Categorical column?
    → chi_square_drift or cramers_v

Is the problem "are there unexpected spiky values"?
  Gaussian-ish data?  → auto_outlier (ensemble)
  Skewed data?        → mad_outlier_fraction or adjusted_boxplot_fraction
  High-dimensional?   → isolation_forest_fraction

Is the problem "did the schema change"?
  → schema_change

Not sure?
  → auto_outlier (ensemble) for point anomalies
  → ks_pvalue for distribution drift
```

---

## Interpreting scores and thresholds

All detector scores are normalised to [0, 1] where 0 = "identical to reference" and 1 =
"maximum divergence". The `STAT_SCALES` entry for each slug defines:

- `direction`: `lower_is_better` (most detectors) or `higher_is_better`
- `warn_threshold`: score above which the result is `warn`
- `fail_threshold`: score above which the result is `fail`

You can inspect any detector's scale in Python:

```python
from dqt.algorithms._scales import STAT_SCALES
scale = STAT_SCALES["ks_pvalue"]
print(scale.warn_threshold, scale.fail_threshold, scale.direction)
```

To calibrate a custom threshold for your specific data:

```python
result = detector.suggest_threshold(reference_df, target_fpr=0.001)
print(f"Suggested warn threshold: {result['suggested_threshold']:.4f}")
# Then set warn_threshold: <value> in your check YAML
```

To monitor whether your configured threshold is still appropriate as data evolves:

```python
from dqt import calibrate_from_history
drift = calibrate_from_history(check, store)
if drift and drift.is_significant:
    print(f"Threshold may need updating: {drift.current_threshold:.4f} -> {drift.suggested_threshold:.4f}")
```

---

## Statistical power and sample size

The library warns when fewer than 30 samples are provided
(`[low-power: N=... < recommended 30]` prepended to `plain_english`).

Practical minimum sample sizes:

| Detector | Min N for reliable results | Notes |
|---|---|---|
| `mad_outlier_fraction` | 30 | Fewer = unstable MAD estimate |
| `ks_pvalue` | 50 per group | KS loses power below this |
| `wasserstein_1` | 100 | Earth-mover estimate stabilises |
| `isolation_forest_fraction` | 256 | sklearn default; fewer = high variance |
| `holt_winters` | 2x seasonal period | Need at least 2 full cycles |
| `bocpd` | 20 | Bayesian update needs some history |

The default sample size is 100,000 rows (reservoir sample). For large tables where
sampling might miss rare events, increase `sample_n` in the check definition.

---

## Methodology design choices

### Why double-MAD over MAD for revenue data

MAD (Median Absolute Deviation) is the standard robust spread estimator.
For heavy-tailed, right-skewed distributions (revenue, latency, spend),
the distribution above the median is much heavier than below.
Double-MAD computes separate left and right MADs, giving
`threshold_right = median + k * MAD_right`. This avoids flagging legitimate
spikes on the right tail while still catching pathological outliers. Default
k=3.5 on the right, catching roughly the same FPR on symmetric data but far
fewer false positives on log-normal revenue data.

Reference: Leys et al. (2013), "Detecting outliers: Do not use standard
deviation around the mean, use absolute deviation around the median."

### Why Wasserstein-1 over KS for tail drift

KS measures the maximum pointwise CDF distance - sensitive to the middle of
the distribution. Wasserstein-1 (earth mover's distance) measures the area
between CDFs - sensitive to the full shape including tails. For revenue and
latency monitoring where tail behavior matters most (P95, P99 shifts),
Wasserstein-1 detects economically meaningful drift that KS misses. KS remains
the default for categorical counts and for normality testing.

Reference: Ramdas et al. (2015), "On Wasserstein Two-Sample Testing and Related
Families of Nonparametric Tests."

### Why PCMCI+ over bivariate Granger for causal discovery

Bivariate Granger tests every pair of metrics independently, leading to
spurious edges from common causes (confounder inflation). PCMCI+ (Runge et al.
2019) runs a conditional independence skeleton search first, then orients
edges, controlling for all other metrics simultaneously. On a 20-metric panel,
PCMCI+ typically finds 15-40% fewer spurious edges than bivariate Granger at
the same alpha. Cost: O(p^2 x T) vs. O(p x T) - worthwhile for panels up to
roughly 100 metrics.

Reference: Runge et al. (2019), "Detecting and quantifying causal associations
in large nonlinear time series datasets."

### Why BH-FDR over Bonferroni for multiple comparisons

Running 64 checks on 100 columns produces up to 6400 simultaneous tests.
Bonferroni divides alpha by 6400 (alpha/6400 = 0.0000078 per test) - so
conservative that real drift is missed. Benjamini-Hochberg (BH) controls the
False Discovery Rate at level alpha. At alpha=0.05 with 100 independent tests,
BH expects no more than 5 false positives on average. For data quality
monitoring, a 5% FDR is appropriate: catching more real drift at the cost of
occasionally investigating a false alarm is better than missing regressions.

Reference: Benjamini and Hochberg (1995), "Controlling the False Discovery Rate."

### Why E-values over p-values for causal edge sensitivity

An E-value quantifies how strong unmeasured confounding would need to be to
explain away an observed causal edge. E-value = 1.0 means any unmeasured
confounder could explain it; E-value = 3.0 means the confounder would need
a risk ratio of 3.0 with both exposure and outcome. dqt flags edges with
E-value < 1.5 as "fragile" in the causality UI.

Reference: VanderWeele and Ding (2017), "Sensitivity Analysis in Observational
Research: Introducing the E-Value."

### Why STL+CUSUM combo for time-series anomalies

STL (Seasonal-Trend decomposition using LOESS) handles seasonality and trend
before anomaly scoring. CUSUM (Cumulative Sum) then detects sustained small
shifts in the residuals that point-wise tests miss. Using them together catches
both spike anomalies (STL residual z-scoring) and gradual level shifts (CUSUM
on residuals). STL alone misses gradual drift; CUSUM alone is confused by
seasonality.

### Why heavy-tailed default threshold is 11.0 instead of textbook 3.5

Textbook MAD threshold k=3.5 assumes roughly normal data. Lognormal data with
sigma=1 has a median at exp(0) and MAD approximately 1.18. The 99.9th percentile
is at exp(3) approximately 20. At k=3.5 on lognormal, the threshold is
approximately 5.1 - cutting off the 95th percentile (5% FPR on healthy data).
At k=11.0 on lognormal, the threshold catches the 99.9th percentile, matching
the intent of a 0.1% FPR. Rule of thumb: for right-skewed data, multiply
textbook k by 3.

### Why bootstrap CIs for threshold calibration

Empirical percentile bootstrap gives distribution-free confidence intervals
for any quantile of the score distribution. Score distributions are rarely
normal - they're often bounded at 0 or 1 and can be bimodal. Traditional
z-based CIs on non-normal score distributions produce thresholds that are too
tight at the tails. Bootstrap CIs are slower (1000 resamples) but honest.

Reference: Efron and Tibshirani (1993), "An Introduction to the Bootstrap."

---

## Further reading

- [Detector benchmark results](../examples/benchmarks/results.csv)
- [Algorithm reference docs](algorithms/) - one-paragraph entry per detector with the canonical reference
- [Check YAML format](checks/)

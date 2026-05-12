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

## Further reading

- [Detector benchmark results](../examples/benchmarks/results.csv)
- [Full benchmark methodology](benchmarks.md)
- [Algorithm reference docs](algorithms/) — one-paragraph entry per detector with the canonical reference
- [Check YAML format](checks/)

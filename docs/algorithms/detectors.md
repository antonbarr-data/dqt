# dqt Statistical Detector Catalog

All examples use **Gigler** — a fictional gig marketplace with sellers, buyers, and bookings.

| Table | Key columns |
|---|---|
| `fct_gigs` | `gig_id`, `seller_id`, `category`, `price_usd`, `created_at`, `status` |
| `fct_bookings` | `booking_id`, `gig_id`, `buyer_id`, `booked_at`, `amount_paid_usd`, `status` |
| `fct_reviews` | `review_id`, `booking_id`, `rating` (1–5), `review_text`, `submitted_at` |
| `dim_sellers` | `seller_id`, `country`, `joined_at`, `tier` (bronze/silver/gold) |

Every detector implements the same contract:

```python
state = detector.fit(reference_df)      # learn from historical data
result = detector.score(current_df, state)  # score current data
# result.verdict  → Verdict.pass_ | Verdict.warn | Verdict.fail
# result.score    → float (lower = healthier for most detectors)
# result.plain_english → "0.8% of values are outliers — within warn threshold"
```

---

## Univariate Outlier Detectors

Score individual rows in a single numeric column against the historical distribution.

**Gigler use case:** flag `price_usd` values in `fct_gigs` that fall outside the pattern from the past 30 days.

| Slug | When to use | Doc |
|---|---|---|
| `zscore_outlier_fraction` | Column is approximately normal (e.g. `rating` after aggregation) | [zscore_outlier_fraction.md](zscore_outlier_fraction.md) |
| `mad_outlier_fraction` | Heavy-tailed or skewed numeric columns (`price_usd`, `amount_paid_usd`) | [mad_outlier_fraction.md](mad_outlier_fraction.md) |
| `double_mad_outlier_fraction` | Strongly asymmetric distributions where left and right tails differ in spread | [double_mad_outlier_fraction.md](double_mad_outlier_fraction.md) |
| `iqr_fence` | Bounded numeric columns where the boxplot rule is the standard (`delivery_days`, `rating`) | [iqr_fence.md](iqr_fence.md) |
| `adjusted_boxplot_fraction` | Skewed distributions — IQR fence corrected for asymmetry via medcouple | [adjusted_boxplot_fraction.md](adjusted_boxplot_fraction.md) |
| `grubbs` | Normally distributed columns when you expect at most one extreme outlier | [grubbs.md](grubbs.md) |
| `generalized_esd` | Normally distributed columns with up to k outliers (Rosner test) | [generalized_esd.md](generalized_esd.md) |
| `auto_outlier` | Unknown distribution — selects among the above automatically | [auto_outlier.md](auto_outlier.md) |

```python
from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
import pandas as pd, numpy as np

rng = np.random.default_rng(42)
ref  = pd.DataFrame({"price_usd": rng.lognormal(4, 0.5, 2000)})
curr = pd.DataFrame({"price_usd": np.append(rng.lognormal(4, 0.5, 1980), [99999.0] * 20)})

det = MADOutlierDetector()
state = det.fit(ref)
result = det.score(curr, state)
print(result.verdict, result.score)  # fail, ~0.010
```

---

## Multivariate Outlier Detectors

Score each row against the joint distribution of multiple columns. Catches anomalies that are invisible per-column but obvious in combination.

**Gigler use case:** detect suspicious seller profiles by jointly monitoring `price_usd`, `booking_rate`, and `avg_rating` — a gig with a suspiciously low price AND suspiciously high booking rate is a red flag neither metric alone would surface.

| Slug | When to use | Doc |
|---|---|---|
| `isolation_forest_fraction` | General-purpose; scales to many columns; no distributional assumptions | [isolation_forest_fraction.md](isolation_forest_fraction.md) |
| `mahalanobis_distance` | Columns are correlated and approximately Gaussian; uses MCD for robustness | [mahalanobis_distance.md](mahalanobis_distance.md) |
| `lof` | Data has clusters; density-based scoring relative to k-nearest neighbours | [lof.md](lof.md) |
| `one_class_svm` | Non-convex decision boundary; learns a tight hypersphere around normal data | [one_class_svm.md](one_class_svm.md) |
| `hbos` | Many columns, very fast; independent per-column histograms | [hbos.md](hbos.md) |
| `ecod` | Default for high-dimensional tabular data; non-parametric, no tuning required | [ecod.md](ecod.md) |

```python
from dqt.algorithms.outliers_multi.ecod import ECODDetector
import pandas as pd, numpy as np

rng = np.random.default_rng(1)
ref = pd.DataFrame({
    "price_usd":    rng.lognormal(4, 0.5, 1000),
    "booking_rate": rng.beta(2, 5, 1000),
    "avg_rating":   rng.normal(4.2, 0.4, 1000).clip(1, 5),
})
curr = ref.copy()
curr.loc[990:, "price_usd"] = 5.0
curr.loc[990:, "booking_rate"] = 0.99

det = ECODDetector()
result = det.score(curr, det.fit(ref))
print(result.verdict)  # warn or fail
```

---

## Distribution Drift Detectors

Compare the current window's distribution against a reference baseline. Use on any column that is measured repeatedly over time.

**Gigler use case:** detect when the distribution of `amount_paid_usd` shifts relative to the previous 14-day baseline — an early signal that pricing behaviour, buyer mix, or data pipeline semantics have changed.

| Slug | When to use | Doc |
|---|---|---|
| `ks_pvalue` | Universal first pass for any numeric column — non-parametric, no binning | [ks_pvalue.md](ks_pvalue.md) |
| `wasserstein_1` | When you need the magnitude of drift in the same units as the column | [wasserstein_1.md](wasserstein_1.md) |
| `psi` | Industry-standard bounded score; `< 0.1` stable, `> 0.2` significant shift | [psi.md](psi.md) |
| `kl_divergence` | Asymmetric cost of approximating the current distribution with the reference | [kl_divergence.md](kl_divergence.md) |
| `js_divergence` | Symmetric, bounded in [0, 1]; complement to `ks_pvalue` | [js_divergence.md](js_divergence.md) |
| `chi_square_drift` | Categorical columns or low-cardinality integers (`status`, `tier`, `rating`) | [chi_square_drift.md](chi_square_drift.md) |
| `mmd` | When distributions overlap significantly and KS misses the shift | [mmd.md](mmd.md) |
| `adwin` | Streaming / real-time; adaptive window — no fixed baseline size needed | [adwin.md](adwin.md) |
| `outlier_fraction_drift` | Track whether the outlier fraction itself is drifting over time | [outlier_fraction_drift.md](outlier_fraction_drift.md) |

```python
from dqt.algorithms.drift.ks import KSDetector
import pandas as pd, numpy as np

rng = np.random.default_rng(2)
ref     = pd.DataFrame({"amount_paid_usd": rng.lognormal(4, 0.6, 2000)})
stable  = pd.DataFrame({"amount_paid_usd": rng.lognormal(4, 0.6, 2000)})
drifted = pd.DataFrame({"amount_paid_usd": rng.lognormal(4.5, 0.6, 2000)})

det = KSDetector()
state = det.fit(ref)
print(det.score(stable, state).verdict)   # pass
print(det.score(drifted, state).verdict)  # warn or fail
```

---

## Information Theory Detectors

Measure statistical association between two columns. Useful for validating expected relationships and catching unexpected dependencies.

**Gigler use case:** verify that `tier` in `dim_sellers` is meaningfully associated with `rating` in `fct_reviews`. If Cramér's V drops unexpectedly, it may indicate a tiering logic change or a review manipulation campaign.

| Slug | When to use | Doc |
|---|---|---|
| `cramers_v` | Two categorical columns; 0 = independent, 1 = perfectly dependent | [cramers_v.md](cramers_v.md) |
| `mutual_information` | Any two numeric columns; model-free, captures non-linear dependencies | [mutual_information.md](mutual_information.md) |

```python
from dqt.algorithms.info.cramers_v import CramersVDetector
import pandas as pd, numpy as np

rng = np.random.default_rng(3)
n = 2000
tiers   = rng.choice(["bronze", "silver", "gold"], n, p=[0.6, 0.3, 0.1])
ratings = np.where(tiers == "gold", rng.integers(4, 6, n), rng.integers(1, 6, n))
ref = pd.DataFrame({"tier": tiers, "rating": ratings.astype(str)})

det = CramersVDetector(col_a="tier", col_b="rating")
result = det.score(ref, det.fit(ref))
print(result.score)  # Cramér's V ≈ 0.2–0.3 for this synthetic dataset
```

---

## Pattern Detectors

Check whether a column conforms to a known statistical law — independent of any historical reference.

**Gigler use case:** validate that `amount_paid_usd` in `fct_bookings` follows Benford's Law. A violation (e.g. all amounts starting with 5) is a strong signal of synthetic or manipulated transaction data.

| Slug | When to use | Doc |
|---|---|---|
| `benford_law_fit` | Naturally-occurring numeric amounts, IDs, or counts that should follow Benford's first-digit law | [benford_law_fit.md](benford_law_fit.md) |

```python
from dqt.algorithms.pattern.benford import BenfordDetector
import pandas as pd, numpy as np

rng = np.random.default_rng(4)
organic   = pd.DataFrame({"amount_paid_usd": rng.lognormal(4, 1.5, 5000)})
synthetic = pd.DataFrame({"amount_paid_usd": rng.integers(10, 1000, 5000).astype(float)})

det = BenfordDetector()
state = det.fit(organic)
print(det.score(organic, state).verdict)    # pass
print(det.score(synthetic, state).verdict)  # warn or fail
```

---

## Time Series Anomaly Detectors

Operate on sequences of values ordered by time. Model the expected pattern from a reference period and flag deviations from the forecast.

**Gigler use case:** monitor the daily booking count for unexpected dips or spikes. A Wednesday dip may indicate a payment processor outage; a spike may indicate data pipeline duplication.

| Slug | When to use | Doc |
|---|---|---|
| `stl_residual_zscore` | Daily/hourly metrics with stable trend + weekly seasonality — robust default | [stl_residual_zscore.md](stl_residual_zscore.md) |
| `cusum` | Catch small sustained mean shifts early (e.g. gradual conversion rate erosion) | [cusum.md](cusum.md) |
| `page_hinkley` | Low-latency streaming change-point; fires as soon as a shift is detected | [page_hinkley.md](page_hinkley.md) |
| `holt_winters` | Stable additive seasonality; fast and interpretable | [holt_winters.md](holt_winters.md) |
| `prophet_anomaly` | Complex multi-period seasonality + holiday effects; requires `dqt[forecast]` | [prophet_anomaly.md](prophet_anomaly.md) |
| `bocpd` | Bayesian posterior over change-point locations; uncertainty-aware alerts | [bocpd.md](bocpd.md) |
| `matrix_profile` | Finds anomalous subsequences — segments unlike anything in the reference | [matrix_profile.md](matrix_profile.md) |

```python
from dqt.algorithms.timeseries.stl import STLResidualZScoreDetector
import pandas as pd, numpy as np

rng = np.random.default_rng(5)
t = np.arange(90)
signal = 5000 + 800 * np.sin(2 * np.pi * t / 7) + rng.normal(0, 150, 90)
ts  = pd.DataFrame({"ds": pd.date_range("2025-01-01", periods=90), "y": signal})
ref  = ts.iloc[:60].set_index("ds")
curr = ts.iloc[60:].set_index("ds").copy()
curr.iloc[5] = 1200  # injected dip

det = STLResidualZScoreDetector()
result = det.score(curr, det.fit(ref))
print(result.verdict)  # warn or fail on the dip
```

---

## Extension Points

When no built-in detector fits, use these escape hatches. Both return a standard `DetectorResult` and participate in the same STAT_SCALES/verdict framework.

| Slug | When to use | Doc |
|---|---|---|
| `callable_check` | Wrap any Python callable as a detector — receives the DataFrame, returns a `float` score | [callable_check.md](callable_check.md) |
| `remote_check` | Call an external HTTP endpoint and interpret the JSON response as a `DetectorResult` | [remote_check.md](remote_check.md) |

```python
from dqt.algorithms.custom.callable_check import CallableCheckDetector

# Gigler: custom fraud score from an internal ML model
def fraud_rate(df: "pd.DataFrame") -> float:
    # assume df has a 'fraud_probability' column from a pre-scored table
    return float((df["fraud_probability"] > 0.8).mean())

det = CallableCheckDetector(fn=fraud_rate)
result = det.score(current_df, det.fit(reference_df))
print(result.plain_english)
```

---

## Quick Reference

All 35 detector slugs by group:

```
outliers_uni:   zscore_outlier_fraction · mad_outlier_fraction · double_mad_outlier_fraction
                iqr_fence · adjusted_boxplot_fraction · grubbs · generalized_esd · auto_outlier

outliers_multi: isolation_forest_fraction · mahalanobis_distance · lof
                one_class_svm · hbos · ecod

drift:          ks_pvalue · wasserstein_1 · psi · kl_divergence · js_divergence
                chi_square_drift · mmd · adwin · outlier_fraction_drift

timeseries:     stl_residual_zscore · cusum · page_hinkley · holt_winters
                prophet_anomaly · bocpd · matrix_profile

info:           cramers_v · mutual_information

pattern:        benford_law_fit

custom:         callable_check · remote_check
```

→ Full declarative checks catalog: [checks.md](checks.md)
→ Master entry point (all 64 slugs with examples): [README.md](README.md)

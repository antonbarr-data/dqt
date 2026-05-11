# dqt Algorithms & Checks Reference

dqt is a data quality, observability, and causal-analysis library for SQL warehouses. It ships a unified detector contract — every statistical method implements `fit(reference) → state` / `score(current, state) → DetectorResult` — so you can mix-and-match algorithms in the same pipeline without glue code.

**Focused catalogs:**
- [detectors.md](detectors.md) — all 35 statistical & ML detector algorithms (univariate outliers, multivariate outliers, drift, information theory, pattern, time series, extension points)
- [checks.md](checks.md) — all 29 declarative checks (nullness, uniqueness, numeric range, string/format, freshness, schema, referential integrity, custom SQL)

All examples in this document use data from **Gigler**, a fictional online marketplace for gigs where freelancers post services (design, coding, writing, translation) and clients book them.

**Gigler's core tables:**

| Table | Key columns |
|---|---|
| `fct_gigs` | `gig_id`, `seller_id`, `category`, `price_usd`, `created_at`, `status` |
| `fct_bookings` | `booking_id`, `gig_id`, `buyer_id`, `booked_at`, `amount_paid_usd`, `status` |
| `fct_reviews` | `review_id`, `booking_id`, `rating` (1–5), `review_text`, `submitted_at` |
| `dim_sellers` | `seller_id`, `country`, `joined_at`, `tier` (bronze/silver/gold) |
| `fct_sessions` | `session_id`, `user_id`, `started_at`, `page_views`, `converted` |

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Univariate Outlier Detectors](#univariate-outlier-detectors)
3. [Multivariate Outlier Detectors](#multivariate-outlier-detectors)
4. [Distribution & Drift Detectors](#distribution--drift-detectors)
5. [Information Theory Detectors](#information-theory-detectors)
6. [Pattern Detectors](#pattern-detectors)
7. [Time Series Anomaly Detectors](#time-series-anomaly-detectors)
8. [Extension Points](#extension-points)
9. [Declarative Checks — Data Quality Basics](#declarative-checks--data-quality-basics)
10. [Declarative Checks — Schema](#declarative-checks--schema)
11. [Declarative Checks — Referential Integrity](#declarative-checks--referential-integrity)
12. [What's Next](#whats-next)

---

## Quick Start

Install dqt and run your first check against Gigler gig-price data in under a minute.

```python
import pandas as pd
import numpy as np
from dqt.runner import Runner
from dqt.store import MemoryStore
from dqt.checks.models import Check
import uuid

# Gigler: monitor gig prices for outliers
rng = np.random.default_rng(42)
reference_df = pd.DataFrame({
    "price_usd": rng.lognormal(4, 0.5, 1000),  # typical Gigler gig prices
})
current_df = pd.DataFrame({
    "price_usd": np.concatenate([
        rng.lognormal(4, 0.5, 950),
        [99999.0] * 50,  # injected price anomalies
    ]),
})

check = Check(
    id=uuid.uuid4(),
    detector_slug="mad_outlier_fraction",
    schema_name="public",
    table_name="fct_gigs",
    column_name="price_usd",
)

runner = Runner(store=MemoryStore())
runner.fit(check, reference_df)  # fit on historical data
result = runner.run(check, current_df)   # score current data
print(result.verdict, result.plain_english)
```

`DetectorResult` always carries: `verdict` (pass / warn / fail), `score` (float), `plain_english` (human-readable sentence), `evidence` (dict of supporting stats), and `threshold` (the scale cutoffs used).

---

## Univariate Outlier Detectors

These detectors flag individual rows in a single numeric column. Use them on columns where each value should conform to a historical distribution — prices, review ratings, session durations, order amounts.

**Gigler use case:** flag `price_usd` values in `fct_gigs` that fall outside the normal range established over the past 30 days of listings.

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_uni.mad import MADDetector

rng = np.random.default_rng(0)
ref = pd.DataFrame({"price_usd": rng.lognormal(4, 0.5, 2000)})
curr = pd.DataFrame({
    "price_usd": np.append(rng.lognormal(4, 0.5, 1980), [99999.0] * 20)
})

det = MADDetector()
state = det.fit(ref)
result = det.score(curr, state)
print(result.verdict, result.score)  # fail, ~0.010 (1% outlier fraction)
```

| Slug | Description | Doc |
|---|---|---|
| `zscore_outlier_fraction` | Fraction of values with Z-score above threshold; assumes near-normality | [zscore_outlier_fraction.md](zscore_outlier_fraction.md) |
| `mad_outlier_fraction` | Same as Z-score but uses median/MAD — robust to heavy tails and skew | [mad_outlier_fraction.md](mad_outlier_fraction.md) |
| `double_mad_outlier_fraction` | Asymmetric MAD: separate scales for left and right tails | [double_mad_outlier_fraction.md](double_mad_outlier_fraction.md) |
| `iqr_fence` | Tukey fences (Q1 − k·IQR, Q3 + k·IQR); classic boxplot outlier rule | [iqr_fence.md](iqr_fence.md) |
| `adjusted_boxplot_fraction` | IQR fence corrected for skewness via medcouple; handles asymmetric distributions | [adjusted_boxplot_fraction.md](adjusted_boxplot_fraction.md) |
| `grubbs` | Grubbs' test for a single extreme outlier in a normally-distributed column | [grubbs.md](grubbs.md) |
| `generalized_esd` | Rosner's Generalized ESD — tests for up to k outliers in a normal column | [generalized_esd.md](generalized_esd.md) |
| `auto_outlier` | Meta-detector: selects among the above based on normality and skewness of the reference | [auto_outlier.md](auto_outlier.md) |

**Choosing between them:**

- `price_usd`, `amount_paid_usd` — lognormal/heavy-tailed: use `mad_outlier_fraction` or `adjusted_boxplot_fraction`.
- `rating` (bounded 1–5): use `iqr_fence`.
- Normally distributed columns: `zscore_outlier_fraction` or `grubbs` / `generalized_esd`.
- Not sure: use `auto_outlier` — it runs the appropriate test automatically.

---

## Multivariate Outlier Detectors

These detectors score each row against the joint distribution of multiple columns simultaneously. A row may look normal in any single column but be anomalous in combination — for example, a Gigler gig with a very low price but extremely high booking rate.

**Gigler use case:** detect suspicious seller profiles by jointly monitoring `price_usd`, `booking_rate`, and `avg_rating` in `dim_sellers`.

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector

rng = np.random.default_rng(1)
ref = pd.DataFrame({
    "price_usd": rng.lognormal(4, 0.5, 1000),
    "booking_rate": rng.beta(2, 5, 1000),
    "avg_rating": rng.normal(4.2, 0.4, 1000).clip(1, 5),
})
curr = ref.copy()
curr.loc[990:, "price_usd"] = 5.0   # suspiciously low prices
curr.loc[990:, "booking_rate"] = 0.99  # combined anomaly

det = IsolationForestDetector()
state = det.fit(ref)
result = det.score(curr, state)
print(result.verdict)  # warn or fail
```

| Slug | Description | Doc |
|---|---|---|
| `isolation_forest_fraction` | Fraction of rows with anomaly score from Isolation Forest (tree-based, scales to high dimensions) | [isolation_forest_fraction.md](isolation_forest_fraction.md) |
| `mahalanobis_distance` | Distance in units of standard deviations accounting for inter-column correlations; uses MCD for robustness | [mahalanobis_distance.md](mahalanobis_distance.md) |
| `lof` | Local Outlier Factor — density ratio relative to k-nearest neighbours; good for clusters | [lof.md](lof.md) |
| `one_class_svm` | One-class SVM; learns a hypersphere boundary around normal data | [one_class_svm.md](one_class_svm.md) |
| `hbos` | Histogram-Based Outlier Score — independent per-column histograms, very fast | [hbos.md](hbos.md) |
| `ecod` | Empirical Cumulative Outlier Detection — non-parametric, default for high-dimensional tabular data | [ecod.md](ecod.md) |

**Choosing between them:**

- General-purpose: `ecod` (default) or `isolation_forest_fraction`.
- When columns are correlated and Gaussian-ish: `mahalanobis_distance`.
- When data has clusters: `lof`.
- Very fast, many columns: `hbos`.

---

## Distribution & Drift Detectors

Drift detectors compare two windows of a column — a reference (historical baseline) and a current window — and report how much the distribution has shifted. Use them on any column that is repeatedly measured over time.

**Gigler use case:** detect when the distribution of `amount_paid_usd` in `fct_bookings` shifts relative to the previous 14-day baseline — a leading indicator that pricing behaviour or buyer mix has changed.

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.ks import KSDetector

rng = np.random.default_rng(2)
ref = pd.DataFrame({"amount_paid_usd": rng.lognormal(4, 0.6, 2000)})
curr_stable = pd.DataFrame({"amount_paid_usd": rng.lognormal(4, 0.6, 2000)})
curr_drifted = pd.DataFrame({"amount_paid_usd": rng.lognormal(4.5, 0.6, 2000)})

det = KSDetector()
state = det.fit(ref)
print(det.score(curr_stable, state).verdict)   # pass
print(det.score(curr_drifted, state).verdict)  # warn or fail
```

| Slug | Description | Doc |
|---|---|---|
| `ks_pvalue` | Two-sample Kolmogorov-Smirnov p-value; non-parametric, sensitive to any distributional difference | [ks_pvalue.md](ks_pvalue.md) |
| `wasserstein_1` | Wasserstein-1 (earth-mover) distance; interpretable as the average shift in the same units as the column | [wasserstein_1.md](wasserstein_1.md) |
| `psi` | Population Stability Index — industry-standard binned score; `< 0.1` stable, `> 0.2` significant shift | [psi.md](psi.md) |
| `kl_divergence` | Kullback-Leibler divergence; asymmetric cost of approximating the current with the reference | [kl_divergence.md](kl_divergence.md) |
| `js_divergence` | Jensen-Shannon distance; symmetric, bounded in [0, 1]; complement to `ks_pvalue` | [js_divergence.md](js_divergence.md) |
| `chi_square_drift` | Chi-square test on bin counts; best for categorical columns or low-cardinality integers | [chi_square_drift.md](chi_square_drift.md) |
| `mmd` | Maximum Mean Discrepancy — kernel-based; powerful when distributions overlap significantly | [mmd.md](mmd.md) |
| `adwin` | Adaptive Windowing — streaming drift detector; no fixed window size needed | [adwin.md](adwin.md) |

**Choosing between them:**

- Numeric, unknown shape: start with `ks_pvalue` (significance) + `wasserstein_1` (magnitude).
- Categorical (`category`, `status`, `tier`): `chi_square_drift`.
- Dashboard overview scores (need a bounded 0–1 value): `js_divergence` or `psi`.
- Streaming / real-time: `adwin`.
- When distributions overlap and KS misses the shift: `mmd`.

---

## Information Theory Detectors

These detectors measure statistical association between two columns — useful for catching unexpected dependencies or validating that expected relationships hold.

**Gigler use case:** verify that `rating` in `fct_reviews` is strongly associated with `status` in `fct_bookings` (completed bookings should have higher ratings). Detect if that association weakens — it may indicate a review-spam campaign or a UX change that broke the submission flow.

```python
import pandas as pd
import numpy as np
from dqt.algorithms.info.cramers_v import CramersVDetector

rng = np.random.default_rng(3)
n = 2000
tiers = rng.choice(["bronze", "silver", "gold"], n, p=[0.6, 0.3, 0.1])
# gold sellers tend to have higher ratings
ratings = np.where(tiers == "gold",
                   rng.integers(4, 6, n),
                   rng.integers(1, 6, n))
ref = pd.DataFrame({"tier": tiers, "rating": ratings.astype(str)})
curr = ref.copy()  # association unchanged

det = CramersVDetector(col_a="tier", col_b="rating")
state = det.fit(ref)
print(det.score(curr, state).verdict)  # pass
```

| Slug | Description | Doc |
|---|---|---|
| `cramers_v` | Cramer's V association between two categorical columns; 0 = independent, 1 = perfectly dependent | [cramers_v.md](cramers_v.md) |
| `mutual_information` | Mutual information between two columns (numeric or categorical); model-free dependency measure | [mutual_information.md](mutual_information.md) |

---

## Pattern Detectors

Pattern detectors check whether a column conforms to a known statistical law or structural pattern — independent of any historical reference.

**Gigler use case:** validate that `gig_id` counts aggregated by day follow Benford's Law — a violation is a strong signal of synthetic or manipulated data (e.g. fake gig inflation).

```python
import pandas as pd
import numpy as np
from dqt.algorithms.pattern.benford import BenfordDetector

rng = np.random.default_rng(4)
# organic order amounts follow Benford's Law
organic = pd.DataFrame({"amount_paid_usd": rng.lognormal(4, 1.5, 5000)})
# synthetic round amounts do not
synthetic = pd.DataFrame({"amount_paid_usd": rng.integers(10, 1000, 5000).astype(float)})

det = BenfordDetector()
state = det.fit(organic)
print(det.score(organic, state).verdict)    # pass
print(det.score(synthetic, state).verdict)  # warn or fail
```

| Slug | Description | Doc |
|---|---|---|
| `benford_law_fit` | Chi-square goodness-of-fit against Benford's Law; flags non-organic numeric distributions | [benford_law_fit.md](benford_law_fit.md) |

---

## Time Series Anomaly Detectors

These detectors operate on a sequence of values ordered by time. They model the expected pattern (trend, seasonality, noise) from a reference period and flag points that deviate from the forecast.

**Gigler use case:** monitor the daily booking count from `fct_bookings` for unexpected spikes or drops. A sudden drop on a Wednesday may indicate a payment processor outage; a spike may indicate a viral campaign or a data pipeline duplication bug.

```python
import pandas as pd
import numpy as np
from dqt.algorithms.timeseries.stl import STLResidualZScoreDetector

rng = np.random.default_rng(5)
# 90 days of daily bookings with weekly seasonality
t = np.arange(90)
signal = 5000 + 800 * np.sin(2 * np.pi * t / 7) + rng.normal(0, 150, 90)
ts = pd.DataFrame({"ds": pd.date_range("2025-01-01", periods=90), "y": signal})
ref = ts.iloc[:60]
curr = ts.iloc[60:].copy()
curr.loc[curr.index[5], "y"] = 1200  # injected dip — possible outage

det = STLResidualZScoreDetector()
state = det.fit(ref)
result = det.score(curr, state)
print(result.verdict)       # warn or fail on the dip window
```

| Slug | Description | Doc |
|---|---|---|
| `stl_residual_zscore` | STL decomposition residual Z-score; handles trend + multi-period seasonality robustly | [stl_residual_zscore.md](stl_residual_zscore.md) |
| `cusum` | Cumulative sum control chart; sensitive to small sustained mean shifts | [cusum.md](cusum.md) |
| `page_hinkley` | Page-Hinkley sequential test; low-latency change-point detection for streaming data | [page_hinkley.md](page_hinkley.md) |
| `holt_winters` | Triple exponential smoothing (Holt-Winters); good for series with stable additive seasonality | [holt_winters.md](holt_winters.md) |
| `prophet_anomaly` | Meta Prophet forecast with uncertainty bands; optional (`dqt[forecast]`); best for complex seasonality + holidays | [prophet_anomaly.md](prophet_anomaly.md) |
| `bocpd` | Bayesian Online Change Point Detection; outputs a posterior over change-point locations | [bocpd.md](bocpd.md) |
| `matrix_profile` | STUMPY Matrix Profile; finds recurring discord motifs — anomalous subsequences unlike any other | [matrix_profile.md](matrix_profile.md) |

**Choosing between them:**

- Daily metrics with weekly seasonality: `stl_residual_zscore` (default).
- Need to catch small drifts quickly: `cusum` or `page_hinkley`.
- Stable seasonal series: `holt_winters`.
- Complex holiday effects: `prophet_anomaly` (requires `pip install dqt[forecast]`).
- Want change-point posteriors, not just alerts: `bocpd`.
- Finding unusual recurring patterns (e.g. every Tuesday is anomalously low): `matrix_profile`.

---

## Extension Points

When no built-in detector fits, dqt provides two escape hatches. Both return standard `DetectorResult` and participate in the same STAT_SCALES / verdict framework.

| Slug | Description | Doc |
|---|---|---|
| `callable_check` | Wrap any Python callable as a detector — receives the current DataFrame, returns a score | [callable_check.md](callable_check.md) |
| `remote_check` | Call an external HTTP endpoint and interpret the JSON response as a DetectorResult | [remote_check.md](remote_check.md) |

**Gigler use case:** Gigler's ML team maintains a custom fraud-scoring model. `remote_check` lets dqt call it on `fct_bookings` samples and surface the fraud rate as a dqt verdict alongside all other checks.

---

## Declarative Checks — Data Quality Basics

Declarative checks are YAML-configurable rules that do not require fitting a statistical baseline. They assert hard constraints — nulls, ranges, set membership, schema — and fail immediately when violated. They are the dqt equivalent of Great Expectations expectations and Soda SodaCL checks.

All declarative checks can be authored in YAML (superset of SodaCL) or via the Python API. The plain-English authoring UI compiles natural language to the equivalent YAML.

**Gigler YAML example:**

```yaml
# dqt check file: checks/fct_gigs.yaml
version: 1
source: gigler_warehouse
dataset: public.fct_gigs
checks:
  - kind: null_fraction
    column: price_usd
    fail_if: "> 0.01"          # tolerate up to 1% nulls

  - kind: value_in_range
    column: price_usd
    min: 1.0
    max: 50000.0

  - kind: set_membership
    column: status
    values: [active, paused, sold_out, deleted]

  - kind: freshness_seconds_behind
    column: created_at
    fail_if: "> 3600"          # data must be < 1 hour old

  - kind: row_count_in_range
    min: 10000
    fail_if: "< min"
```

### Column-level constraints

| Slug | Description |
|---|---|
| `null_fraction` | Fraction of nulls in a column must stay within threshold |
| `completeness` | Inverse of null_fraction: fraction of non-null values must meet minimum |
| `uniqueness` | Fraction of distinct values (or strict all-unique assertion) |
| `value_in_range` | Every non-null value must fall within `[min, max]` |
| `set_membership` | Every non-null value must appear in an allowed set |
| `set_exclusion` | Every non-null value must not appear in a forbidden set |
| `regex_match` | Fraction of values matching a regex pattern must meet threshold |
| `string_length_range` | String length of every value must fall within `[min_len, max_len]` |
| `date_format` | Every value must parse against a strftime format string |
| `string_case_violation` | Fraction of values violating the expected case rule (upper/lower/title) |
| `numeric_mean` | Column mean must fall within `[min, max]` |
| `min_in_range` | Column minimum must fall within `[min, max]` |
| `max_in_range` | Column maximum must fall within `[min, max]` |
| `median_in_range` | Column median must fall within `[min, max]` |
| `stddev_in_range` | Column standard deviation must fall within `[min, max]` |
| `sum_in_range` | Column sum must fall within `[min, max]` |
| `cardinality_in_range` | Number of distinct values must fall within `[min, max]` |
| `quantile_in_range` | A given quantile (e.g. p95) must fall within `[min, max]` |
| `monotonicity` | Values in a column must be non-decreasing (or non-increasing) |
| `date_part_missing_fraction` | Fraction of rows missing a specific date part (e.g. hour) must be below threshold |
| `validity` | Composite validity rule: column must satisfy all sub-checks to count as valid |

### Table-level constraints

| Slug | Description |
|---|---|
| `volume` | Row count alias — total row count must fall within expected range |
| `row_count_in_range` | Row count must fall within `[min, max]`; alias for `volume` with explicit bounds |
| `freshness_seconds_behind` | Timestamp column must be no more than N seconds behind wall clock |
| `column_pair_comparison` | Two columns in the same row must satisfy a comparison operator (e.g. `end_at >= start_at`) |
| `composite_uniqueness` | Combination of two or more columns must be unique across the table |

### Custom SQL

| Slug | Description |
|---|---|
| `sql_assertion_violation` | Fraction of rows returned by a custom SQL query (each returned row = one violation) must be below threshold |

**Gigler example — custom SQL:**

```yaml
- kind: sql_assertion_violation
  name: booking_amount_matches_gig_price
  query: |
    SELECT b.booking_id
    FROM fct_bookings b
    JOIN fct_gigs g ON b.gig_id = g.gig_id
    WHERE ABS(b.amount_paid_usd - g.price_usd) > 0.01
  fail_if: "> 0"
```

---

## Declarative Checks — Schema

| Slug | Description | Doc |
|---|---|---|
| `schema_change` | Detects added, removed, or type-changed columns relative to the recorded schema snapshot | [schema_change.md](schema_change.md) |

**Gigler use case:** alert immediately if a column is dropped from `fct_bookings` or if `amount_paid_usd` changes type — both would silently corrupt downstream revenue metrics.

---

## Declarative Checks — Referential Integrity

| Slug | Description | Doc |
|---|---|---|
| `referential_integrity_rate` | Fraction of foreign-key values in a child table that exist in the parent table's primary key | [referential_integrity_rate.md](referential_integrity_rate.md) |

**Gigler example:**

```yaml
- kind: referential_integrity_rate
  child_column: gig_id
  parent_dataset: public.fct_gigs
  parent_column: gig_id
  fail_if: "< 0.999"  # allow up to 0.1% orphaned bookings
```

---

## What's Next

- **Detector contract** — how `fit` / `score` / `DetectorResult` work and how to implement a custom detector: `docs/architecture/detector_contract.md`
- **STAT_SCALES** — every detector's warn/fail thresholds and verdict bands: `packages/dqt/src/dqt/algorithms/_scales.py`
- **Check YAML schema** — full JSON Schema for check definitions: `packages/dqt/src/dqt/checks/schema/check.schema.json`
- **Causality layer** — how dqt discovers metric-to-metric causal edges and attributes incidents: `docs/architecture/causality.md`
- **AI agent** — how the agent explains incidents using Pearl's ladder of causation: `docs/architecture/agent.md`
- **Compatibility shims** — how to migrate from Great Expectations, Soda, or Elementary: `dqt.compat.gx`, `dqt.compat.soda`, `dqt.compat.elementary`
- **Individual detector docs** — each slug above links to its own page with full parameter reference, scale table, and additional examples

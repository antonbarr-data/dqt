# Gigler check coverage — 100% detector exercise

Proposed checks for the Gigler BigQuery source covering every registered detector slug.
Use the Import YAML button (replace mode) to load all at once, or add selectively in merge mode.

YAML format: `check` = detector slug, `table` = dataset_id as stored in the source
(`gigler.<table_name>`), `column` = column name (omit for table-level detectors).

---

## Tables and columns

| Table | Columns |
|---|---|
| `gigler.marketing_campaigns` | campaign_id, date, geo, city, profession, price_range, language, channel, campaign_type, impressions, clicks, conversions, spend_usd, revenue_usd, roi, quality_score |
| `gigler.gigler_transactions` | transaction_id, date, gig_category, seller_country, buyer_country, seller_profession, amount_usd, currency, payment_method, status, completion_days, rating, is_repeat_buyer, platform_fee_usd, seller_level, week_number |
| `gigler.gig_vendor_stats` | date, gig_category, n_active_vendors, n_new_vendors, avg_vendor_rating, top_rated_fraction, total_profile_views, avg_profile_views, search_impressions, click_through_rate, avg_response_time_hours |
| `gigler.gig_prices` | date, gig_category, avg_price_usd, median_price_usd, min_price_usd, max_price_usd, n_listings, discount_active, price_change_pct |

---

## Detector coverage

67 detectors total. 65 can be defined via YAML; `callable_check` and `remote_check` require the Python API.

### Basic group

```yaml
# completeness — fraction of non-null values
check: completeness
table: gigler.gigler_transactions
column: transaction_id
rationale: "transaction_id must never be null"

---
# null_fraction — fraction of NULL values (complement of completeness)
check: null_fraction
table: gigler.gigler_transactions
column: amount_usd
rationale: "amount_usd NULLs indicate pipeline failures"

---
# uniqueness — fraction of distinct values
check: uniqueness
table: gigler.gigler_transactions
column: transaction_id
rationale: "transaction_id is a primary key — must be unique"

---
# validity — fraction of rows satisfying a SQL predicate
check: validity
table: gigler.gigler_transactions
column: rating
params:
  sql_predicate: "rating >= 1.0 AND rating <= 5.0"
rationale: "ratings are on a 1-5 scale"

---
# value_in_range — fraction of values outside [min_value, max_value]
check: value_in_range
table: gigler.gigler_transactions
column: amount_usd
params:
  min_value: 0.01
  max_value: 100000.0
rationale: "transaction amounts must be positive and below fraud ceiling"

---
# set_membership — fraction of values not in the allowed set
check: set_membership
table: gigler.gigler_transactions
column: status
params:
  allowed_values: ["completed", "cancelled", "disputed", "in_progress"]
rationale: "status enum must stay within known values"

---
# set_exclusion — fraction of values in the forbidden set
check: set_exclusion
table: gigler.gigler_transactions
column: status
params:
  forbidden_values: ["DELETED", "test", "__debug__"]
rationale: "test/debug sentinels must not appear in production data"

---
# regex_match — fraction not matching a pattern
check: regex_match
table: gigler.marketing_campaigns
column: campaign_id
params:
  pattern: "^[A-Za-z0-9_-]{4,64}$"
rationale: "campaign_id format: alphanumeric with underscores/hyphens, 4-64 chars"

---
# string_length_range — fraction with length outside [min_len, max_len]
check: string_length_range
table: gigler.gigler_transactions
column: seller_profession
params:
  min_len: 2
  max_len: 100
rationale: "profession strings must be non-trivial and not truncated"

---
# date_format — fraction not matching expected date string format
check: date_format
table: gigler.gig_prices
column: date
params:
  date_format: "%Y-%m-%d"
rationale: "date column must conform to ISO 8601 date format"

---
# string_case_violation — fraction with wrong casing
check: string_case_violation
table: gigler.gigler_transactions
column: currency
params:
  case: "upper"
rationale: "ISO 4217 currency codes must be uppercase (USD, EUR, GBP)"

---
# sql_assertion_violation — fraction failing a custom SQL condition
check: sql_assertion_violation
table: gigler.gigler_transactions
column: completion_days
params:
  condition: "completion_days >= 0"
rationale: "completion_days cannot be negative — would indicate data corruption"

---
# date_part_missing_fraction — fraction of expected date buckets with no data
check: date_part_missing_fraction
table: gigler.gig_prices
column: date
params:
  granularity: "day"
  lookback_days: 30
rationale: "gig_prices must have a row for every day in the last 30 days"

---
# freshness_seconds_behind — seconds since latest row timestamp
check: freshness_seconds_behind
table: gigler.gig_prices
column: date
params:
  col: date
  warn_seconds: 86400
  fail_seconds: 172800
rationale: "gig_prices is a daily feed; data older than 2 days indicates a pipeline failure"

---
# numeric_mean — Z-score of mean shift from baseline
check: numeric_mean
table: gigler.gigler_transactions
column: amount_usd
rationale: "large mean shift in transaction amounts signals pricing changes or data errors"

---
# volume — row count deviation from baseline
check: volume
table: gigler.gigler_transactions
rationale: "transaction volume drop indicates a pipeline or ingestion failure"

---
# volume_anomaly — row count outside [min_rows, max_rows]
check: volume_anomaly
table: gigler.marketing_campaigns
params:
  min_rows: 100
  max_rows: 100000
rationale: "marketing_campaigns must have at least 100 rows; more than 100k is a load anomaly"

---
# row_count_in_range — row count in a date window outside [min, max]
check: row_count_in_range
table: gigler.gigler_transactions
params:
  date_col: date
  start_date: "2024-01-01"
  end_date: "2024-01-31"
  min_rows: 500
  max_rows: 50000
rationale: "January 2024 transaction count must be within expected range"

---
# monotonicity — ordering violation check
check: monotonicity
table: gigler.gig_vendor_stats
column: n_active_vendors
params:
  direction: "increasing"
rationale: "active vendor count should trend upward over time (non-decreasing)"

---
# max_in_range — MAX(col) outside [min_val, max_val]
check: max_in_range
table: gigler.gigler_transactions
column: rating
params:
  min_val: 4.0
  max_val: 5.0
rationale: "max rating must be 5.0 (the scale ceiling); below 4.0 max would be suspicious"

---
# min_in_range — MIN(col) outside [min_val, max_val]
check: min_in_range
table: gigler.gigler_transactions
column: amount_usd
params:
  min_val: 0.01
  max_val: 10.0
rationale: "minimum transaction must be at least $0.01 and not exceed $10 (floor is low)"

---
# median_in_range — median outside [min_val, max_val]
check: median_in_range
table: gigler.gigler_transactions
column: amount_usd
params:
  min_val: 50.0
  max_val: 1000.0
rationale: "median transaction value should stay in normal range; outliers indicate skew"

---
# stddev_in_range — STDDEV(col) outside [min_val, max_val]
check: stddev_in_range
table: gigler.gigler_transactions
column: completion_days
params:
  min_val: 1.0
  max_val: 30.0
rationale: "stddev of completion days should reflect typical variation, not extreme spread"

---
# sum_in_range — SUM(col) outside [min_val, max_val]
check: sum_in_range
table: gigler.marketing_campaigns
column: spend_usd
params:
  min_val: 10000.0
  max_val: 100000000.0
rationale: "total campaign spend must be material but not astronomically large"

---
# cardinality_in_range — COUNT(DISTINCT) outside [min_val, max_val]
check: cardinality_in_range
table: gigler.gigler_transactions
column: gig_category
params:
  min_val: 10
  max_val: 30
rationale: "gig_category should have 10-30 distinct values; outside that range signals enum drift"

---
# quantile_in_range — quantile outside [min_val, max_val]
check: quantile_in_range
table: gigler.gigler_transactions
column: amount_usd
params:
  quantile: 0.95
  min_val: 100.0
  max_val: 10000.0
rationale: "95th percentile of transaction amount must stay within expected bounds"

---
# column_pair_comparison — fraction violating col_a <op> col_b
check: column_pair_comparison
table: gigler.marketing_campaigns
column: revenue_usd
params:
  col_a: revenue_usd
  col_b: spend_usd
  operator: ">="
rationale: "revenue should be >= spend for profitable campaigns (warn when below)"

---
# composite_uniqueness — fraction of duplicate composite key rows
check: composite_uniqueness
table: gigler.gig_prices
params:
  key_columns: ["date", "gig_category"]
rationale: "date + gig_category must be a unique key in gig_prices"
```

---

### Schema group

```yaml
# schema_change — 1.0 if schema changed since baseline
check: schema_change
table: gigler.gigler_transactions
rationale: "alert on any column additions, removals, or type changes in transactions table"
```

---

### Referential group

```yaml
# referential_integrity_rate — fraction of FK values present in parent table
check: referential_integrity_rate
table: gigler.gigler_transactions
column: gig_category
params:
  parent_table: gigler.gig_prices
  parent_col: gig_category
rationale: "every transaction category must exist in the gig_prices reference table"
```

---

### Drift group

```yaml
# ks_pvalue — two-sample KS test, score = 1 - p-value
check: ks_pvalue
table: gigler.gigler_transactions
column: amount_usd
baseline:
  window_days: 30
rationale: "detect distribution shift in transaction amounts vs last 30 days"

---
# ks_drift — time-windowed KS drift check
check: ks_drift
table: gigler.gigler_transactions
column: amount_usd
params:
  date_col: date
  reference_days: 30
  current_days: 7
rationale: "compare current week vs last month transaction amount distribution"

---
# psi — Population Stability Index
check: psi
table: gigler.gigler_transactions
column: amount_usd
params:
  n_bins: 10
baseline:
  window_days: 30
rationale: "PSI > 0.2 signals significant population shift in transaction amounts"

---
# wasserstein_1 — Earth-mover distance normalized by reference stddev
check: wasserstein_1
table: gigler.gig_prices
column: avg_price_usd
baseline:
  window_days: 30
rationale: "detect magnitude of price distribution shift across categories"

---
# kl_divergence — Kullback-Leibler divergence
check: kl_divergence
table: gigler.gigler_transactions
column: completion_days
rationale: "KL divergence detects shifts in completion time distribution"

---
# js_divergence — Jensen-Shannon distance
check: js_divergence
table: gigler.gigler_transactions
column: rating
rationale: "JS distance is bounded and symmetric; suitable for rating distribution drift"

---
# chi_square_drift — chi-square test for categorical drift
check: chi_square_drift
table: gigler.gigler_transactions
column: status
baseline:
  window_days: 14
rationale: "detect shifts in the status distribution (e.g. cancellation spike)"

---
# cramers_v — Cramer's V from 2xk contingency table
check: cramers_v
table: gigler.gigler_transactions
column: gig_category
rationale: "Cramer's V > 0.30 signals meaningful category distribution shift"

---
# mmd — Maximum Mean Discrepancy with RBF kernel
check: mmd
table: gigler.marketing_campaigns
column: roi
baseline:
  window_days: 14
rationale: "MMD detects non-parametric distribution shift in ROI"

---
# adwin — adaptive windowing drift signal
check: adwin
table: gigler.gig_vendor_stats
column: avg_vendor_rating
params:
  delta: 0.002
rationale: "ADWIN detects concept drift in vendor rating stream"
```

---

### Pattern group

```yaml
# benford_law_fit — chi-square goodness-of-fit vs Benford's Law first-digit distribution
check: benford_law_fit
table: gigler.marketing_campaigns
column: spend_usd
rationale: "natural financial figures follow Benford's Law; deviations signal fabricated data"
```

---

### Info group

```yaml
# mutual_information — normalized MI between reference and current distributions
check: mutual_information
table: gigler.gigler_transactions
column: amount_usd
params:
  n_bins: 20
rationale: "MI < 0.30 indicates the current distribution is very different from reference"
```

---

### Univariate outlier group

```yaml
# mad_outlier_fraction — modified Z-score with MAD; robust to heavy tails
check: mad_outlier_fraction
table: gigler.gigler_transactions
column: amount_usd
params:
  threshold: 6.5
rationale: "transaction amounts are right-skewed; MAD is more appropriate than Z-score"

---
# double_mad_outlier_fraction — asymmetric MAD for skewed distributions
check: double_mad_outlier_fraction
table: gigler.marketing_campaigns
column: impressions
params:
  threshold: 6.5
rationale: "impressions are right-skewed; double-MAD handles asymmetric tails"

---
# zscore_outlier_fraction — standard Z-score outliers (assumes normality)
check: zscore_outlier_fraction
table: gigler.gig_vendor_stats
column: avg_vendor_rating
params:
  threshold: 3.0
rationale: "vendor ratings are approximately normally distributed; Z-score is appropriate"

---
# adjusted_boxplot_fraction — medcouple-adjusted Tukey fences
check: adjusted_boxplot_fraction
table: gigler.gigler_transactions
column: platform_fee_usd
rationale: "fee amounts are skewed; adjusted boxplot is robust to asymmetric distributions"

---
# iqr_fence — standard Tukey IQR fences
check: iqr_fence
table: gigler.gigler_transactions
column: completion_days
params:
  k: 1.5
rationale: "standard IQR fence to flag suspiciously long or short completion times"

---
# grubbs — Grubbs test for a single extreme outlier (assumes normality)
check: grubbs
table: gigler.gig_vendor_stats
column: click_through_rate
rationale: "CTR is roughly normal; Grubbs detects a single extreme category outlier"

---
# generalized_esd — Generalized ESD test for multiple outliers
check: generalized_esd
table: gigler.gig_prices
column: avg_price_usd
rationale: "GESD identifies multiple price outliers across categories simultaneously"

---
# outlier_fraction_drift — deviation of current outlier fraction from historical baseline
check: outlier_fraction_drift
table: gigler.gigler_transactions
column: amount_usd
rationale: "tracks whether the outlier fraction itself is increasing over time"
```

---

### Multivariate outlier group

These detectors operate on all numeric columns of the table. Apply at table level (omit `column`).

```yaml
# isolation_forest_fraction — Isolation Forest on all numeric columns
check: isolation_forest_fraction
table: gigler.gigler_transactions
params:
  contamination: 0.05
rationale: "Isolation Forest detects anomalous transaction rows across all numeric features"

---
# mahalanobis_distance — fraction of rows outside chi-square critical ellipsoid
check: mahalanobis_distance
table: gigler.marketing_campaigns
rationale: "Mahalanobis detects campaigns with unusual combinations of spend/impressions/clicks"

---
# lof — Local Outlier Factor
check: lof
table: gigler.gig_vendor_stats
rationale: "LOF finds vendors with unusual activity profiles relative to their neighbours"

---
# one_class_svm — One-Class SVM novelty detection
check: one_class_svm
table: gigler.gigler_transactions
params:
  nu: 0.01
rationale: "OC-SVM detects transactions that look unlike anything in the reference period"

---
# hbos — Histogram-Based Outlier Score
check: hbos
table: gigler.marketing_campaigns
params:
  n_bins: 20
rationale: "HBOS is fast and interpretable for high-dimensional campaign anomalies"

---
# ecod — Empirical CDF-based Outlier Detection
check: ecod
table: gigler.gig_prices
rationale: "ECOD detects price rows with extreme values across multiple price columns"
```

---

### Time-series group

Time-series detectors expect sequential observations. Apply to aggregate time series
(e.g. daily row-count or daily average from `gig_prices` or `gig_vendor_stats`).

```yaml
# stl_residual_zscore — STL seasonal decomposition residual Z-score
check: stl_residual_zscore
table: gigler.gig_prices
column: avg_price_usd
params:
  period: 7
rationale: "STL separates weekly seasonality from trend; residuals above 3-sigma flag anomalies"

---
# cusum — CUSUM control chart for mean drift
check: cusum
table: gigler.gig_vendor_stats
column: n_active_vendors
params:
  k: 0.5
  h: 5.0
rationale: "CUSUM detects gradual sustained decline in active vendor count"

---
# page_hinkley — Page-Hinkley test for mean shift detection
check: page_hinkley
table: gigler.gig_vendor_stats
column: avg_vendor_rating
params:
  delta: 0.005
  lambda_: 100.0
rationale: "Page-Hinkley detects an upward or downward step in the average rating"

---
# holt_winters — Holt-Winters exponential smoothing forecast
check: holt_winters
table: gigler.gig_prices
column: n_listings
params:
  period: 7
rationale: "HW predicts expected listing counts with weekly seasonality; flags spikes or drops"

---
# bocpd — Bayesian Online Changepoint Detection
check: bocpd
table: gigler.gig_prices
column: avg_price_usd
params:
  hazard_lambda: 50
rationale: "BOCPD finds sudden shifts in the average price level (pricing policy changes)"

---
# matrix_profile — discord detection via Matrix Profile
check: matrix_profile
table: gigler.gig_vendor_stats
column: click_through_rate
params:
  window: 7
rationale: "Matrix Profile finds unusual 7-day subsequences in CTR (e.g. algorithm changes)"

---
# prophet_anomaly — Prophet uncertainty interval anomaly detection
check: prophet_anomaly
table: gigler.gig_prices
column: avg_price_usd
rationale: "Prophet models trend + seasonality; values outside its interval are anomalies"
```

---

## Custom group (Python API only)

These two detectors cannot be imported via YAML. Use the Python `dqt` library directly.

### `callable_check`

Runs a user-supplied Python function `(df: pd.DataFrame) -> float`.

```python
from dqt.checks import Check
from dqt.algorithms.custom.callable_check import CallableCheckDetector

# Example: fraction of transactions where platform_fee > 30% of amount
check = Check(
    schema_name="gigler",
    table_name="gigler_transactions",
    detector=CallableCheckDetector(
        fn=lambda df: float((df["platform_fee_usd"] / df["amount_usd"] > 0.30).mean())
    ),
)
```

### `remote_check`

Calls an external HTTP endpoint and expects `{"score": float}`.

```yaml
# remote_check — external scoring endpoint
check: remote_check
table: gigler.gigler_transactions
column: amount_usd
params:
  endpoint: "https://fraud-scoring.internal/dq/check"
  timeout: 10.0
rationale: "delegate anomaly scoring to the fraud detection service"
```

---

## Summary

| Group | Count | Detectors |
|---|---|---|
| Basic | 28 | completeness, null_fraction, uniqueness, validity, value_in_range, set_membership, set_exclusion, regex_match, string_length_range, date_format, string_case_violation, sql_assertion_violation, date_part_missing_fraction, freshness_seconds_behind, numeric_mean, volume, volume_anomaly, row_count_in_range, monotonicity, max_in_range, min_in_range, median_in_range, stddev_in_range, sum_in_range, cardinality_in_range, quantile_in_range, column_pair_comparison, composite_uniqueness |
| Schema | 1 | schema_change |
| Referential | 1 | referential_integrity_rate |
| Drift | 10 | ks_pvalue, ks_drift, psi, wasserstein_1, kl_divergence, js_divergence, chi_square_drift, cramers_v, mmd, adwin |
| Pattern | 1 | benford_law_fit |
| Info | 1 | mutual_information |
| Univariate outlier | 8 | mad_outlier_fraction, double_mad_outlier_fraction, zscore_outlier_fraction, adjusted_boxplot_fraction, iqr_fence, grubbs, generalized_esd, outlier_fraction_drift |
| Multivariate outlier | 6 | isolation_forest_fraction, mahalanobis_distance, lof, one_class_svm, hbos, ecod |
| Time-series | 7 | stl_residual_zscore, cusum, page_hinkley, holt_winters, bocpd, matrix_profile, prophet_anomaly |
| Custom | 2 | callable_check, remote_check |
| **Total** | **65** | |

> Note: `auto_outlier` (registered but not in `_scales.py`) auto-selects the best univariate method and is not included here. Use it as a shortcut when you are unsure which outlier detector to pick.

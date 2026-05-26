# YAML check definition reference

A check definition is a YAML object that binds a detector to a table or column. The schema is at `packages/dqt/src/dqt/checks/schema/check.schema.json`.

## Field reference

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | `string (uuid)` | No | auto-generated | Stable identifier. Auto-generated if omitted. |
| `schema_name` | `string` | **Yes** | — | Database schema (e.g. `public`, `main`). |
| `table_name` | `string` | **Yes** | — | Table or view name. |
| `column_name` | `string \| null` | No | `null` | Column to check. Omit for table-level detectors (`volume`, `volume_anomaly`, `schema_change`). |
| `detector_slug` | `string` | **Yes** | — | Detector identifier. See [Detector slugs](#detector-slugs) below. |
| `params` | `object` | No | `{}` | Detector-specific parameters. See each detector entry below. |
| `baseline` | `object \| null` | No | `null` | Baseline window config. `null` means the runner auto-fits on first run. |
| `baseline.window_days` | `integer (≥1)` | No | `14` | Days of history used to fit the reference distribution. |
| `baseline.min_rows` | `integer (≥1)` | No | `1000` | Minimum rows required in the reference window before fitting. |
| `schedule` | `string \| null` | No | `null` | Cron expression (server only). Not used by the CLI runner. |
| `sample_n` | `integer (≥1000)` | No | `100000` | Maximum rows to sample. |
| `sampling_pct` | `number (0.001–100) \| null` | No | `null` | Percentage of rows to sample. When set, overrides `sample_n`. |
| `scope` | `object \| null` | No | `null` | Controls which rows are included. |
| `scope.mode` | `"entire" \| "incremental" \| "custom"` | **Yes** (if scope set) | — | `entire` reads all rows; `incremental` reads rows after `since`; `custom` applies `custom_sql`. |
| `scope.key_col` | `string \| null` | No | `null` | Timestamp/monotonic column for `incremental` mode. |
| `scope.since` | `string \| null` | No | `null` | ISO datetime string or `"last_run"` for incremental mode. |
| `scope.custom_sql` | `string \| null` | No | `null` | SQL WHERE clause fragment for `custom` mode. |
| `filters` | `array` | No | `[]` | Row-level equality filters applied before sampling. |
| `filters[].col` | `string` | **Yes** | — | Column name to filter on. |
| `filters[].values` | `array (≥1 item)` | **Yes** | — | Allowed values (OR'd together). |

---

## Detector slugs

Detectors are organised into seven categories that match the UI filter panel.

| Category | Description |
|---|---|
| Completeness | Is the data there? (nulls, volume, freshness, schema) |
| Validity | Does it match the rules? (format, range, uniqueness, referential) |
| Drift | Has the distribution shifted? (statistical distance tests) |
| Univariate outliers | Are individual values unusual? |
| Multivariate outliers | Are rows unusual in combination? |
| Time series | Did the temporal pattern change? |
| Custom | User-supplied logic (callable or remote) |

---

### Completeness

#### `completeness`

Fraction of non-null values. Score = completeness rate (higher is better). Warn < 0.95, fail < 0.90.

No required params.

```yaml
- schema_name: public
  table_name: users
  column_name: email
  detector_slug: completeness
```

#### `null_fraction`

Fraction of NULL values. Score = null fraction (lower is better). Warn ≥ 0.01, fail ≥ 0.05.

No required params.

```yaml
- schema_name: public
  table_name: orders
  column_name: order_id
  detector_slug: null_fraction
```

#### `volume`

Row count deviation from baseline. Score = fractional change (lower is better). Warn ≥ 0.10, fail ≥ 0.25. Table-level check — omit `column_name`.

No required params.

```yaml
- schema_name: public
  table_name: events
  detector_slug: volume
```

#### `volume_anomaly`

Checks that row count is within `[min_rows, max_rows]`. Score = 1.0 if count is outside range, 0.0 otherwise. Warn and fail both at ≥ 0.5 (binary). Table-level check.

| Param | Required | Default | Description |
|---|---|---|---|
| `min_rows` | No | `1` | Minimum expected row count. |
| `max_rows` | No | `2147483648` | Maximum expected row count. |

```yaml
- schema_name: public
  table_name: daily_events
  detector_slug: volume_anomaly
  params:
    min_rows: 1000
    max_rows: 10000000
```

#### `row_count_in_range`

Checks that the row count within a date window falls within `[min_rows, max_rows]`. Score = 1.0 if outside range, 0.0 otherwise. Warn and fail both at ≥ 0.5 (binary).

| Param | Required | Default | Description |
|---|---|---|---|
| `date_col` | **Yes** | — | Date/timestamp column to filter by. |
| `start_date` | **Yes** | — | Start of the window (ISO date string, inclusive). |
| `end_date` | **Yes** | — | End of the window (ISO date string, inclusive). |
| `min_rows` | No | `0` | Minimum expected rows in the window. |
| `max_rows` | No | `2147483648` | Maximum expected rows in the window. |

```yaml
- schema_name: public
  table_name: marketing_campaigns
  detector_slug: row_count_in_range
  params:
    date_col: event_date
    start_date: "2024-06-01"
    end_date: "2024-06-30"
    min_rows: 50
    max_rows: 500
```

#### `freshness_seconds_behind`

Seconds elapsed since the most recent row timestamp. Uses instance-level thresholds. Score = seconds behind (lower is better).

| Param | Required | Default | Description |
|---|---|---|---|
| `col` | No | `updated_at` | Column to `MAX()`. |
| `warn_seconds` | No | `3600` | Warn if data is older than this many seconds. |
| `fail_seconds` | No | `86400` | Fail if data is older than this many seconds. |

```yaml
- schema_name: public
  table_name: fct_orders
  column_name: updated_at
  detector_slug: freshness_seconds_behind
  params:
    col: updated_at
    warn_seconds: 3600
    fail_seconds: 86400
```

#### `schema_change`

1.0 if the column set or column types changed since the baseline; 0.0 otherwise. Warn and fail both at ≥ 0.5 (binary). Table-level check.

No required params.

```yaml
- schema_name: public
  table_name: fct_orders
  detector_slug: schema_change
```

---

### Validity

#### `uniqueness`

Fraction of distinct values. Score = uniqueness rate (higher is better). Warn < 0.95, fail < 0.80.

No required params.

```yaml
- schema_name: public
  table_name: users
  column_name: user_id
  detector_slug: uniqueness
```

#### `validity`

Fraction of rows satisfying a SQL predicate. Score = validity rate (higher is better). Warn < 0.95, fail < 0.90.

| Param | Required | Default | Description |
|---|---|---|---|
| `sql_predicate` | **Yes** | — | SQL expression that must be true for valid rows. |

```yaml
- schema_name: public
  table_name: orders
  column_name: amount
  detector_slug: validity
  params:
    sql_predicate: "amount > 0"
```

#### `value_in_range`

Fraction of values outside `[min_value, max_value]`. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

| Param | Required | Default | Description |
|---|---|---|---|
| `min_value` | No | `-inf` | Inclusive lower bound. |
| `max_value` | No | `inf` | Inclusive upper bound. |

```yaml
- schema_name: public
  table_name: payments
  column_name: amount_usd
  detector_slug: value_in_range
  params:
    min_value: 0.01
    max_value: 1000000.0
```

#### `set_membership`

Fraction of values not in the allowed set. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

| Param | Required | Default | Description |
|---|---|---|---|
| `allowed_values` | No | `[]` | List of permitted values. |

```yaml
- schema_name: public
  table_name: orders
  column_name: status
  detector_slug: set_membership
  params:
    allowed_values: [pending, processing, shipped, delivered, cancelled]
```

#### `set_exclusion`

Fraction of values in the forbidden set. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

| Param | Required | Default | Description |
|---|---|---|---|
| `forbidden_values` | No | `[]` | List of forbidden values. |

```yaml
- schema_name: public
  table_name: events
  column_name: type
  detector_slug: set_exclusion
  params:
    forbidden_values: [DELETED, __test__]
```

#### `regex_match`

Fraction of values not matching the regex pattern. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

| Param | Required | Default | Description |
|---|---|---|---|
| `pattern` | No | `.*` | Python regex. Non-matching rows are violations. |

```yaml
- schema_name: public
  table_name: users
  column_name: phone
  detector_slug: regex_match
  params:
    pattern: "^\\+[1-9][0-9]{7,14}$"
```

#### `string_length_range`

Fraction of values with string length outside `[min_len, max_len]`. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

| Param | Required | Default | Description |
|---|---|---|---|
| `min_len` | No | `0` | Minimum allowed string length. |
| `max_len` | No | `255` | Maximum allowed string length. |

```yaml
- schema_name: public
  table_name: products
  column_name: sku
  detector_slug: string_length_range
  params:
    min_len: 6
    max_len: 12
```

#### `date_format`

Fraction of non-null values whose string form does not match the date format. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

Supported tokens: `%Y`, `%m`, `%d`, `%H`, `%M`, `%S`, `YYYY`, `MM`, `DD`, `HH24`, `MI`, `SS`.

| Param | Required | Default | Description |
|---|---|---|---|
| `date_format` | No | `%Y-%m-%d` | Expected date format string. |

```yaml
- schema_name: public
  table_name: events
  column_name: event_date
  detector_slug: date_format
  params:
    date_format: "%Y-%m-%d"
```

#### `string_case`

Fraction of rows with wrong case. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

| Param | Required | Default | Description |
|---|---|---|---|
| `case` | No | `upper` | Expected case: `"upper"`, `"lower"`, or `"title"`. |

```yaml
- schema_name: public
  table_name: countries
  column_name: country_code
  detector_slug: string_case
  params:
    case: "upper"
```

#### `sql_assertion`

Fraction of rows failing a custom SQL condition. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

| Param | Required | Default | Description |
|---|---|---|---|
| `condition` | **Yes** | — | SQL boolean expression. Rows where this is false are violations. |

```yaml
- schema_name: public
  table_name: orders
  column_name: order_id
  detector_slug: sql_assertion
  params:
    condition: "shipped_at IS NULL OR shipped_at >= created_at"
```

#### `date_part_missing`

Fraction of expected date buckets with no data. Score = missing fraction (lower is better). Warn ≥ 0.01, fail ≥ 0.05.

| Param | Required | Default | Description |
|---|---|---|---|
| `granularity` | No | `day` | Bucket size: `"day"`, `"hour"`, or `"month"`. |
| `lookback_days` | No | `30` | Number of days of history to check. |

```yaml
- schema_name: public
  table_name: daily_metrics
  column_name: metric_date
  detector_slug: date_part_missing
  params:
    granularity: "day"
    lookback_days: 30
```

#### `numeric_mean_shift`

Z-score of the mean deviation from the baseline. Score = Z-score (lower is better). Warn ≥ 2.0, fail ≥ 3.0.

No required params.

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: numeric_mean_shift
```

#### `monotonicity`

1.0 if the ordering is violated; 0.0 if the sequence is monotonic. Warn and fail both at ≥ 0.5 (binary).

| Param | Required | Default | Description |
|---|---|---|---|
| `direction` | No | `increasing` | `"increasing"` or `"decreasing"`. |

```yaml
- schema_name: public
  table_name: audit_log
  column_name: sequence_number
  detector_slug: monotonicity
  params:
    direction: "increasing"
```

#### `referential_integrity_rate`

Fraction of FK values present in the parent table. Score = integrity rate (higher is better). Warn < 0.99, fail < 0.95.

| Param | Required | Default | Description |
|---|---|---|---|
| `parent_table` | **Yes** | — | Fully qualified parent table (`schema.table` or just `table`). |
| `parent_col` | No | `id` | Primary key column in the parent table. |

```yaml
- schema_name: public
  table_name: order_items
  column_name: product_id
  detector_slug: referential_integrity_rate
  params:
    parent_table: public.products
    parent_col: product_id
```

---

### Drift

#### `ks_pvalue`

Two-sample Kolmogorov–Smirnov test. Score = 1 − p-value (lower p → higher score). Warn score ≥ 0.95 (p < 0.05), fail score ≥ 0.99 (p < 0.01). Ref: Kolmogorov (1933), Smirnov (1948).

No required params.

```yaml
- schema_name: public
  table_name: payments
  column_name: amount
  detector_slug: ks_pvalue
  baseline:
    window_days: 14
  sample_n: 100000
```

#### `ks_drift`

Time-windowed KS drift check. Compares a reference window (control) against a current window (test) using date filtering. Score = 1 − p-value. Warn score ≥ 0.95, fail score ≥ 0.99.

| Param | Required | Default | Description |
|---|---|---|---|
| `date_col` | **Yes** | — | Date/timestamp column name to filter windows by (e.g. `created_at`). Must be a column name, not a date value. |
| `reference_days` | No | `30` | Length of the control (reference) window in days. |
| `current_days` | No | `7` | Length of the test (current) window ending today. |

```yaml
- schema_name: public
  table_name: payments
  column_name: amount
  detector_slug: ks_drift
  params:
    date_col: created_at
    reference_days: 30
    current_days: 7
```

#### `wasserstein_1`

Earth-mover distance (Wasserstein-1) normalized by reference standard deviation. Score = normalized distance (lower is better). Warn ≥ 0.20, fail ≥ 0.50.

No required params.

```yaml
- schema_name: public
  table_name: payments
  column_name: amount
  detector_slug: wasserstein_1
  baseline:
    window_days: 14
```

#### `psi`

Population Stability Index. Score = PSI (lower is better). PSI < 0.1 = stable, 0.1–0.2 = moderate shift, > 0.2 = significant shift.

| Param | Required | Default | Description |
|---|---|---|---|
| `n_bins` | No | `10` | Number of bins for the histogram. |

```yaml
- schema_name: public
  table_name: users
  column_name: age
  detector_slug: psi
  params:
    n_bins: 10
```

#### `kl_divergence`

Kullback–Leibler divergence (binned). Score = KL divergence (lower is better). Warn ≥ 0.10, fail ≥ 0.30.

| Param | Required | Default | Description |
|---|---|---|---|
| `n_bins` | No | `10` | Number of bins. |

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: kl_divergence
```

#### `js_divergence`

Jensen–Shannon distance (bounded [0, 1]). Score = JS distance (lower is better). Warn ≥ 0.10, fail ≥ 0.20.

| Param | Required | Default | Description |
|---|---|---|---|
| `n_bins` | No | `10` | Number of bins. |

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: js_divergence
```

#### `chi_square_drift`

Chi-square test for categorical drift. Score = 1 − p-value. Warn score ≥ 0.95 (p < 0.05), fail score ≥ 0.99 (p < 0.01).

No required params.

```yaml
- schema_name: public
  table_name: events
  column_name: event_type
  detector_slug: chi_square_drift
  baseline:
    window_days: 14
```

#### `cramers_v`

Cramér's V from a 2×k contingency table. Score = V (lower is better). Warn ≥ 0.15, fail ≥ 0.30.

No required params.

```yaml
- schema_name: public
  table_name: events
  column_name: event_type
  detector_slug: cramers_v
```

#### `mmd`

Maximum Mean Discrepancy with RBF kernel. Score = MMD (lower is better). Warn ≥ 0.10, fail ≥ 0.20.

No required params.

```yaml
- schema_name: public
  table_name: payments
  column_name: amount
  detector_slug: mmd
  baseline:
    window_days: 14
```

#### `mutual_information`

Normalized mutual information between reference and current distributions. Score = NMI (higher is better — more similar). Warn < 0.50, fail < 0.30.

| Param | Required | Default | Description |
|---|---|---|---|
| `n_bins` | No | `20` | Number of bins for discretisation. |

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: mutual_information
```

#### `benford_law_fit`

Chi-square goodness-of-fit against Benford's Law first-digit frequencies. Score = 1 − p-value. Warn score ≥ 0.95 (p < 0.05), fail score ≥ 0.99 (p < 0.01).

No required params.

```yaml
- schema_name: public
  table_name: invoices
  column_name: amount
  detector_slug: benford_law_fit
```

---

### Univariate outliers

#### `mad_outlier_fraction`

Modified Z-score using MAD (Median Absolute Deviation). Robust to heavy tails. Score = fraction of values with |modified Z| > threshold. Warn ≥ 0.01, fail ≥ 0.05. Ref: Leys et al. (2013).

| Param | Required | Default | Description |
|---|---|---|---|
| `threshold` | No | `11.0` | Modified Z-score cutoff. 3.5 = sensitive, 11 = robust. |

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: mad_outlier_fraction
  params:
    threshold: 6.5
```

#### `double_mad_outlier_fraction`

Asymmetric double-MAD for skewed distributions. Computes separate left and right MAD from the median. Warn ≥ 0.01, fail ≥ 0.05. Ref: Rousseeuw & Croux (1993).

| Param | Required | Default | Description |
|---|---|---|---|
| `threshold` | No | `6.5` | Modified Z-score cutoff. |

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: double_mad_outlier_fraction
  params:
    threshold: 6.5
```

#### `zscore_outlier_fraction`

Standard Z-score outlier detection. Score = fraction of values with |Z| > threshold. Warn ≥ 0.01, fail ≥ 0.05. **Only valid under approximate normality** — use `mad_outlier_fraction` for non-normal columns.

| Param | Required | Default | Description |
|---|---|---|---|
| `threshold` | No | `3.0` | Z-score cutoff. |

```yaml
- schema_name: public
  table_name: metrics
  column_name: value
  detector_slug: zscore_outlier_fraction
  params:
    threshold: 3.0
```

#### `adjusted_boxplot_fraction`

Medcouple-adjusted Tukey fences. Robust to skewed distributions. Warn ≥ 0.01, fail ≥ 0.05. Ref: Hubert & Vandervieren (2008).

| Param | Required | Default | Description |
|---|---|---|---|
| `h` | No | `2.5` | Tukey fence multiplier for outlier boundary. |

```yaml
- schema_name: public
  table_name: sessions
  column_name: duration_s
  detector_slug: adjusted_boxplot_fraction
```

#### `iqr_fence`

Standard Tukey IQR fences. Score = fraction of values outside `[Q1 - k*IQR, Q3 + k*IQR]`. Warn ≥ 0.01, fail ≥ 0.05.

| Param | Required | Default | Description |
|---|---|---|---|
| `k` | No | `1.5` | IQR multiplier. 1.5 = Tukey standard; 3.0 = extreme outliers only. |

```yaml
- schema_name: public
  table_name: orders
  column_name: amount
  detector_slug: iqr_fence
  params:
    k: 1.5
```

#### `grubbs`

Grubbs test for a single outlier. Score = 1 − p-value. Warn score ≥ 0.95 (p < 0.05), fail score ≥ 0.99 (p < 0.01). **Assumes normality.**

No required params.

```yaml
- schema_name: public
  table_name: sensor_readings
  column_name: value
  detector_slug: grubbs
```

#### `generalized_esd`

Generalized Extreme Studentized Deviate (GESD) test. Score = fraction of flagged outliers. Warn ≥ 0.01, fail ≥ 0.05. Ref: Rosner (1983).

| Param | Required | Default | Description |
|---|---|---|---|
| `max_outliers` | No | `0` | Maximum number of outliers to test for. `0` = auto (5% of n). |
| `alpha` | No | `0.05` | Significance level for each individual test. |

```yaml
- schema_name: public
  table_name: sensor_readings
  column_name: value
  detector_slug: generalized_esd
```

#### `outlier_fraction_drift`

Tracks whether the IQR outlier fraction of a column has changed between the reference window and the current window. Score = deviation from baseline (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

Can be run directly against any numeric warehouse column (computes the IQR outlier fraction inline), or used as a meta-detector by passing a pre-computed `outlier_fraction` series.

| Param | Required | Default | Description |
|---|---|---|---|
| `method` | No | `iqr` | Range method for historical baseline: `"iqr"`, `"percentile"`, or `"zscore"`. |
| `k` | No | `1.5` | IQR multiplier (used when `method=iqr`). |
| `lower_pct` | No | `5.0` | Lower percentile boundary (used when `method=percentile`). |
| `upper_pct` | No | `95.0` | Upper percentile boundary (used when `method=percentile`). |

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: outlier_fraction_drift
```

---

### Multivariate outliers

#### `isolation_forest_fraction`

Isolation Forest on all numeric columns. Score = fraction of rows classified as anomalies. Warn ≥ 0.05, fail ≥ 0.10. Ref: Liu et al. (2008).

| Param | Required | Default | Description |
|---|---|---|---|
| `reference_pct` | No | `5.0` | Percentile of reference anomaly scores used as the fixed decision threshold. Lower = stricter. |

```yaml
- schema_name: public
  table_name: events
  detector_slug: isolation_forest_fraction
  params:
    reference_pct: 5.0
```

#### `mahalanobis_distance`

Fraction of rows outside the chi-square critical ellipsoid at p = 0.01. Score = outlier fraction (lower is better). Warn ≥ 0.01, fail ≥ 0.05.

| Param | Required | Default | Description |
|---|---|---|---|
| `p_threshold` | No | `0.001` | Chi-square p-value threshold for the boundary ellipsoid. |

```yaml
- schema_name: public
  table_name: transactions
  detector_slug: mahalanobis_distance
```

#### `lof`

Local Outlier Factor. Score = fraction of rows with LOF above threshold. Warn ≥ 0.05, fail ≥ 0.10.

| Param | Required | Default | Description |
|---|---|---|---|
| `n_neighbors` | No | `null` (auto) | Number of nearest neighbours. `null` = auto-select. |

```yaml
- schema_name: public
  table_name: transactions
  detector_slug: lof
```

#### `one_class_svm`

One-Class SVM novelty detection. Score = fraction of rows classified as outliers. Warn ≥ 0.05, fail ≥ 0.10.

| Param | Required | Default | Description |
|---|---|---|---|
| `nu` | No | `0.01` | Upper bound on fraction of outliers (0–1). |
| `kernel` | No | `rbf` | SVM kernel: `"rbf"`, `"linear"`, `"poly"`, `"sigmoid"`. |

```yaml
- schema_name: public
  table_name: transactions
  detector_slug: one_class_svm
  params:
    nu: 0.01
```

#### `hbos`

Histogram-Based Outlier Score. Score = fraction of rows with score above the reference 95th percentile. Warn ≥ 0.05, fail ≥ 0.10.

| Param | Required | Default | Description |
|---|---|---|---|
| `n_bins` | No | `20` | Number of histogram bins per feature. |

```yaml
- schema_name: public
  table_name: transactions
  detector_slug: hbos
```

#### `ecod`

Empirical Cumulative distribution-based Outlier Detection (ECOD). Score = fraction of rows with score above the reference 95th percentile. Warn ≥ 0.05, fail ≥ 0.10.

No required params.

```yaml
- schema_name: public
  table_name: transactions
  detector_slug: ecod
```

---

### Time series

#### `stl_residual_zscore`

Seasonal-Trend decomposition via Loess (STL). Score = max absolute Z-score of STL residuals. Warn ≥ 3.0, fail ≥ 5.0. Requires ≥ `2 * period + 1` observations. Ref: Cleveland et al. (1990).

| Param | Required | Default | Description |
|---|---|---|---|
| `period` | No | `7` | Observations per season (e.g. 7 for weekly, 24 for hourly). |

```yaml
- schema_name: public
  table_name: daily_orders
  column_name: order_count
  detector_slug: stl_residual_zscore
  params:
    period: 7
```

#### `prophet_anomaly`

STL-based anomaly detector with a Prophet-compatible interface. Fits seasonal-trend decomposition on the reference window, then scores the fraction of current values whose STL residuals fall outside the prediction interval. Score = anomaly fraction (lower is better). Warn ≥ 0.05, fail ≥ 0.10.

| Param | Required | Default | Description |
|---|---|---|---|
| `interval_width` | No | `0.95` | Prediction interval width (0–1). Maps to a Z-score threshold: 0.95 → 1.96, 0.99 → 2.58. |
| `period` | No | `null` (auto) | Seasonality period in observations. `null` = auto-detected from reference data via FFT. |

```yaml
- schema_name: public
  table_name: daily_orders
  column_name: order_count
  detector_slug: prophet_anomaly
  params:
    interval_width: 0.95
    period: 7
```

#### `cusum`

Cumulative Sum (CUSUM) control chart. Score = normalised CUSUM statistic. Warn ≥ 1.0, fail ≥ 2.0.

| Param | Required | Default | Description |
|---|---|---|---|
| `k` | No | `0.5` | Slack (allowance); smaller = more sensitive to drift. |
| `h` | No | `5.0` | Decision boundary; smaller = more false positives. |

```yaml
- schema_name: public
  table_name: daily_metrics
  column_name: value
  detector_slug: cusum
  params:
    k: 0.5
    h: 5.0
```

#### `page_hinkley`

Page-Hinkley test for mean shift detection. Score = normalised PH statistic. Warn ≥ 0.5, fail ≥ 1.0.

| Param | Required | Default | Description |
|---|---|---|---|
| `delta` | No | `0.005` | Minimal change magnitude to detect. |
| `lambda_` | No | `100.0` | Threshold for triggering an alarm. |

```yaml
- schema_name: public
  table_name: daily_metrics
  column_name: value
  detector_slug: page_hinkley
```

#### `holt_winters`

Holt-Winters exponential smoothing forecast. Score = fraction of current values outside the prediction interval. Warn ≥ 0.05, fail ≥ 0.10.

| Param | Required | Default | Description |
|---|---|---|---|
| `period` | No | `7` | Seasonality period in observations. |
| `alpha` | No | `0.99` | Smoothing factor (0–1); higher = faster adaptation. |

```yaml
- schema_name: public
  table_name: daily_orders
  column_name: order_count
  detector_slug: holt_winters
  params:
    period: 7
```

#### `bocpd`

Bayesian Online Changepoint Detection. Score = max posterior probability of a changepoint in the current window. Warn ≥ 0.50, fail ≥ 0.80.

| Param | Required | Default | Description |
|---|---|---|---|
| `hazard_lambda` | No | `50.0` | Expected run length between changepoints. Smaller = more sensitive. |

```yaml
- schema_name: public
  table_name: daily_metrics
  column_name: value
  detector_slug: bocpd
  params:
    hazard_lambda: 50
```

#### `adwin`

ADWIN (ADaptive WINdowing) drift detection. Score = 1.0 when drift is detected, 0.0 otherwise. Warn and fail both at ≥ 0.5 (binary).

| Param | Required | Default | Description |
|---|---|---|---|
| `delta` | No | `0.002` | Confidence parameter for the ADWIN test. |

```yaml
- schema_name: public
  table_name: daily_metrics
  column_name: value
  detector_slug: adwin
```

#### `matrix_profile`

Matrix Profile discord detection. Score = fraction of subsequences whose nearest-neighbour distance exceeds the reference 95th percentile. Warn ≥ 0.05, fail ≥ 0.10.

| Param | Required | Default | Description |
|---|---|---|---|
| `window` | No | `7` | Subsequence length for the matrix profile. |

```yaml
- schema_name: public
  table_name: daily_orders
  column_name: order_count
  detector_slug: matrix_profile
  params:
    window: 7
```

---

### Custom

#### `callable_check`

Runs a user-supplied Python callable. The callable receives a `pd.DataFrame` of the column sample and must return a `float` score. Warn ≥ 0.5, fail ≥ 0.75 (configurable via `warn_threshold`/`fail_threshold`).

| Param | Required | Default | Description |
|---|---|---|---|
| `fn` | **Yes** | — | Python callable (`df -> float`). Not serialisable to YAML — use the Python API only. |

```python
# Python API only — callable_check cannot be defined in YAML
from dqt.checks import Check
from dqt.algorithms.custom.callable_check import CallableCheckDetector

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector=CallableCheckDetector(fn=lambda df: float((df.iloc[:, 0] > 0).mean())),
)
```

#### `remote_check`

Calls an external HTTP endpoint with the column sample as JSON. The endpoint must return `{"score": float}`. Warn ≥ 0.5, fail ≥ 0.75 (configurable via `warn_threshold`/`fail_threshold`).

| Param | Required | Default | Description |
|---|---|---|---|
| `endpoint` | **Yes** | — | URL of the remote scoring endpoint. |
| `params` | No | `null` | Extra key-value pairs sent in the request payload. |
| `timeout` | No | `30.0` | Request timeout in seconds. |
| `graphql_query` | No | `null` | GraphQL query string. When set, the request is sent as a GraphQL query. |
| `graphql_variable` | No | `rows` | GraphQL variable name for the row data. |

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: remote_check
  params:
    endpoint: "https://scoring.internal/dq/check"
    timeout: 10.0
```

---

## Scope examples

### Entire table (default)

```yaml
scope:
  mode: entire
```

### Incremental -- rows since a fixed timestamp

```yaml
scope:
  mode: incremental
  key_col: created_at
  since: "2024-06-01T00:00:00"
```

### Incremental -- rows since the last run

```yaml
scope:
  mode: incremental
  key_col: updated_at
  since: last_run
```

### Custom SQL WHERE clause

```yaml
scope:
  mode: custom
  custom_sql: "region = 'EU' AND is_test = FALSE"
```

---

## Filter examples

Filters apply equality conditions before sampling. Multiple filters are AND'd together; multiple values within one filter are OR'd.

```yaml
filters:
  - col: region
    values: [EU, APAC]    # region IN ('EU', 'APAC')
  - col: channel
    values: [web]         # AND channel = 'web'
```

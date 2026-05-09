# YAML check definition reference

A check definition is a YAML object that binds a detector to a table or column. The schema is at `packages/dqt/src/dqt/checks/schema/check.schema.json`.

## Field reference

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | `string (uuid)` | No | auto-generated | Stable identifier. Auto-generated if omitted. |
| `schema_name` | `string` | Yes | — | Database schema (e.g. `public`, `main`). |
| `table_name` | `string` | Yes | — | Table or view name. |
| `column_name` | `string \| null` | No | `null` | Column to check. Omit for table-level detectors (`volume`, `schema_change`). |
| `detector_slug` | `string` | Yes | — | Detector identifier. See [Detector slugs](#detector-slugs) below. |
| `params` | `object` | No | `{}` | Detector-specific parameters. See each detector entry below. |
| `baseline` | `object \| null` | No | `null` | Baseline window config. `null` means the runner auto-fits on first run. |
| `baseline.window_days` | `integer (≥1)` | No | `14` | Days of history used to fit the reference distribution. |
| `baseline.min_rows` | `integer (≥1)` | No | `1000` | Minimum rows required in the reference window before fitting. |
| `schedule` | `string \| null` | No | `null` | Cron expression (server only). Not used by the CLI runner. |
| `sample_n` | `integer (≥1000)` | No | `100000` | Maximum rows to sample. |
| `sampling_pct` | `number (0.001–100) \| null` | No | `null` | Percentage of rows to sample. When set, overrides `sample_n`. |
| `scope` | `object \| null` | No | `null` | Controls which rows are included. |
| `scope.mode` | `"entire" \| "incremental" \| "custom"` | Yes (if scope set) | — | `entire` reads all rows; `incremental` reads rows after `since`; `custom` applies `custom_sql`. |
| `scope.key_col` | `string \| null` | No | `null` | Timestamp/monotonic column for `incremental` mode. |
| `scope.since` | `string \| null` | No | `null` | ISO datetime string or `"last_run"` for incremental mode. |
| `scope.custom_sql` | `string \| null` | No | `null` | SQL WHERE clause fragment for `custom` mode. |
| `filters` | `array` | No | `[]` | Row-level equality filters applied before sampling. |
| `filters[].col` | `string` | Yes | — | Column name to filter on. |
| `filters[].values` | `array (≥1 item)` | Yes | — | Allowed values (OR'd together). |

---

## Detector slugs

### Basic group

#### `completeness`

Fraction of non-null values. Score = completeness rate (higher is better). Warn < 0.95, fail < 0.90.

```yaml
- schema_name: public
  table_name: users
  column_name: email
  detector_slug: completeness
```

#### `null_fraction`

Fraction of NULL values. Score = null fraction (lower is better). Warn ≥ 0.01, fail ≥ 0.05.

```yaml
- schema_name: public
  table_name: orders
  column_name: order_id
  detector_slug: null_fraction
```

#### `uniqueness`

Fraction of distinct values. Score = uniqueness rate (higher is better). Warn < 0.95, fail < 0.80.

```yaml
- schema_name: public
  table_name: users
  column_name: user_id
  detector_slug: uniqueness
```

#### `validity`

Fraction of rows satisfying a SQL predicate. Score = validity rate (higher is better). Warn < 0.95, fail < 0.90.

```yaml
- schema_name: public
  table_name: orders
  column_name: amount
  detector_slug: validity
  params:
    sql_predicate: "amount > 0"
```

#### `volume`

Row count deviation from baseline. Score = fractional change (lower is better). Warn ≥ 0.10, fail ≥ 0.25. Table-level check — omit `column_name`.

```yaml
- schema_name: public
  table_name: events
  detector_slug: volume
```

#### `freshness_seconds_behind`

Seconds elapsed since the most recent row timestamp. Uses instance-level thresholds, not global STAT_SCALES thresholds, because SLAs vary per table.

```yaml
- schema_name: public
  table_name: fct_orders
  column_name: updated_at
  detector_slug: freshness_seconds_behind
  params:
    col: updated_at          # column to MAX()
    warn_seconds: 3600       # 1 hour
    fail_seconds: 86400      # 24 hours
```

#### `value_in_range`

Fraction of values outside `[min_val, max_val]`. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

```yaml
- schema_name: public
  table_name: payments
  column_name: amount_usd
  detector_slug: value_in_range
  params:
    min_val: 0.01
    max_val: 1000000.0
```

#### `set_membership`

Fraction of values not in the allowed set. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

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

```yaml
- schema_name: public
  table_name: events
  column_name: type
  detector_slug: set_exclusion
  params:
    forbidden_values: [DELETED, __test__]
```

#### `regex_match`

Fraction of values not matching the regex pattern (Postgres `~` operator). Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

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

Fraction of non-null values whose string form does not match the structural regex derived from the date format. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

Supported tokens: `%Y`, `%m`, `%d`, `%H`, `%M`, `%S`, `YYYY`, `MM`, `DD`, `HH24`, `MI`, `SS`.

```yaml
- schema_name: public
  table_name: events
  column_name: event_date
  detector_slug: date_format
  params:
    date_format: "%Y-%m-%d"
```

#### `numeric_mean_shift`

Z-score of the mean deviation from the baseline. Score = Z-score (lower is better). Warn ≥ 2.0, fail ≥ 3.0.

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: numeric_mean_shift
```

#### `string_case`

Fraction of rows with wrong case. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

```yaml
- schema_name: public
  table_name: countries
  column_name: country_code
  detector_slug: string_case
  params:
    expected_case: "upper"   # "upper" | "lower" | "title"
```

#### `sql_assertion`

Fraction of rows failing a custom SQL condition. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

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

```yaml
- schema_name: public
  table_name: daily_metrics
  column_name: metric_date
  detector_slug: date_part_missing
  params:
    part: "day"   # "day" | "hour" | "month"
```

#### `monotonicity`

1.0 if the ordering is violated; 0.0 if the sequence is monotonic. Warn and fail both at ≥ 0.5 (binary check).

```yaml
- schema_name: public
  table_name: audit_log
  column_name: sequence_number
  detector_slug: monotonicity
  params:
    direction: "asc"   # "asc" | "desc"
```

#### `column_pair`

Fraction of rows where a comparison rule between two columns is violated. Score = violation fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

```yaml
- schema_name: public
  table_name: orders
  column_name: shipped_at
  detector_slug: column_pair
  params:
    other_col: created_at
    operator: ">="    # "==" | "!=" | "<" | "<=" | ">" | ">="
```

#### `composite_uniqueness`

Fraction of rows that are duplicates on a composite key. Score = duplicate fraction (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

```yaml
- schema_name: public
  table_name: order_items
  detector_slug: composite_uniqueness
  params:
    key_columns: [order_id, product_id]
```

#### Numeric aggregate bounds

These detectors check that an aggregate statistic falls within `[min, max]`. Score is 1.0 when the aggregate is outside the range, 0.0 otherwise. Warn and fail both at ≥ 0.5 (binary).

| Slug | Aggregate |
|---|---|
| `max_in_range` | `MAX(col)` |
| `min_in_range` | `MIN(col)` |
| `median_in_range` | median (PERCENTILE_CONT 0.5) |
| `stddev_in_range` | `STDDEV(col)` |
| `sum_in_range` | `SUM(col)` |
| `cardinality_in_range` | `COUNT(DISTINCT col)` |
| `quantile_in_range` | specified quantile |

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: max_in_range
  params:
    min: 0.0
    max: 999999.0
```

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: quantile_in_range
  params:
    quantile: 0.99
    min: 0.0
    max: 5000.0
```

---

### Schema group

#### `schema_change`

1.0 if the column set or column types changed since the baseline; 0.0 otherwise. Warn and fail both at ≥ 0.5 (binary). Table-level check.

```yaml
- schema_name: public
  table_name: fct_orders
  detector_slug: schema_change
```

---

### Referential group

#### `referential_integrity_rate`

Fraction of FK values present in the parent table. Score = integrity rate (higher is better). Warn < 0.99, fail < 0.95.

```yaml
- schema_name: public
  table_name: order_items
  column_name: product_id
  detector_slug: referential_integrity_rate
  params:
    parent_schema: public
    parent_table: products
    parent_column: product_id
```

---

### Drift group

#### `ks_pvalue`

Two-sample Kolmogorov–Smirnov test. Score = 1 − p-value (lower p → higher score). Warn score ≥ 0.95 (p < 0.05), fail score ≥ 0.99 (p < 0.01). Ref: Kolmogorov (1933), Smirnov (1948).

```yaml
- schema_name: public
  table_name: payments
  column_name: amount
  detector_slug: ks_pvalue
  baseline:
    window_days: 14
  sample_n: 100000
```

---

### Univariate outlier group

#### `mad_outlier_fraction`

Modified Z-score using MAD (Median Absolute Deviation). Robust to heavy tails. Score = fraction of values with |modified Z| > threshold. Warn ≥ 0.01, fail ≥ 0.05. Ref: Leys et al. (2013).

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: mad_outlier_fraction
  params:
    threshold: 3.5    # default 3.5
```

#### `double_mad_outlier_fraction`

Asymmetric double-MAD for skewed distributions. Computes separate left and right MAD from the median. Warn ≥ 0.01, fail ≥ 0.05. Ref: Rousseeuw & Croux (1993).

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: double_mad_outlier_fraction
  params:
    threshold: 3.5
```

#### `zscore_outlier_fraction`

Standard Z-score outlier detection. Score = fraction of values with |Z| > threshold. Warn ≥ 0.01, fail ≥ 0.05. **Only valid under approximate normality** — use `mad_outlier_fraction` for non-normal columns.

```yaml
- schema_name: public
  table_name: metrics
  column_name: value
  detector_slug: zscore_outlier_fraction
  params:
    threshold: 3.0
```

#### `adjusted_boxplot_fraction`

Medcouple-adjusted Tukey fences. Robust to skewed distributions by adjusting whisker lengths via the medcouple statistic. Warn ≥ 0.01, fail ≥ 0.05. Ref: Hubert & Vandervieren (2008).

```yaml
- schema_name: public
  table_name: sessions
  column_name: duration_s
  detector_slug: adjusted_boxplot_fraction
```

#### `outlier_fraction_drift`

Deviation of the current outlier fraction from the historical baseline range. Detects when a previously stable outlier rate shifts significantly. Score = deviation from baseline (lower is better). Warn ≥ 0.001, fail ≥ 0.01.

```yaml
- schema_name: public
  table_name: transactions
  column_name: amount
  detector_slug: outlier_fraction_drift
```

---

### Multivariate outlier group

#### `isolation_forest_fraction`

Isolation Forest on all numeric columns. Score = fraction of rows classified as anomalies. Warn ≥ 0.05, fail ≥ 0.10. Ref: Liu et al. (2008).

```yaml
- schema_name: public
  table_name: events
  detector_slug: isolation_forest_fraction
  params:
    contamination: 0.05   # expected outlier fraction; default 0.05
```

---

### Time-series group

#### `stl_residual_zscore`

Seasonal-Trend decomposition via Loess (STL). Score = max absolute Z-score of STL residuals. Warn ≥ 3.0, fail ≥ 5.0. Requires ≥ `2 * period + 1` observations. Ref: Cleveland et al. (1990).

```yaml
- schema_name: public
  table_name: daily_orders
  column_name: order_count
  detector_slug: stl_residual_zscore
  params:
    period: 7    # seasonality period in observations; default 7 (weekly)
```

---

## Scope examples

### Entire table (default)

```yaml
scope:
  mode: entire
```

### Incremental — rows since a fixed timestamp

```yaml
scope:
  mode: incremental
  key_col: created_at
  since: "2024-06-01T00:00:00"
```

### Incremental — rows since the last run

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

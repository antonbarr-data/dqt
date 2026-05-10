# Detectors Reference

All detectors are referenced by `detector_slug` in a `Check` or YAML config. Each returns a `DetectorResult` with `(verdict, score, plain_english, details)`.

**Verdict thresholds** are defined in `packages/dqt/src/dqt/algorithms/_scales.py` and are the single source of truth.

---

## Basic detectors

### `null_fraction`
Fraction of NULL values in a column. Lower is better. Warn ≥ 1%, fail ≥ 5%.

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="amount_usd", detector_slug="null_fraction",
)
```

---

### `completeness`
Fraction of non-null values (inverse of null_fraction). Higher is better. Warn < 95%, fail < 90%.

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="rating", detector_slug="completeness",
)
```

---

### `uniqueness`
Fraction of distinct values out of total rows. Higher = more unique. No baseline needed — purely declarative.

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="transaction_id", detector_slug="uniqueness",
)
```

---

### `volume`
Row count deviation from baseline. Compares current row count against the fitted baseline count. Warn ≥ 10% change, fail ≥ 25%.

No `column_name` needed — table-level check.

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    detector_slug="volume",
)
```

---

### `numeric_mean`
Z-score of the mean shift from the baseline mean. Flags unexpected level shifts.

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="amount_usd", detector_slug="numeric_mean",
)
```

---

### `value_in_range`
Fraction of values outside `[min_val, max_val]`. Lower is better.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_val` | float | `-inf` | Lower bound (inclusive) |
| `max_val` | float | `inf` | Upper bound (inclusive) |

```python
# ratings must be 1.0–5.0
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="rating", detector_slug="value_in_range",
    params={"min_val": 1.0, "max_val": 5.0},
)

# platform_fee_usd must be non-negative
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="platform_fee_usd", detector_slug="value_in_range",
    params={"min_val": 0.0},
)
```

---

### `set_membership`
Fraction of values NOT in an allowed set. Lower is better. Fail ≥ 1%.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `allowed_values` | list | yes | The only accepted values |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="status", detector_slug="set_membership",
    params={"allowed_values": ["completed", "cancelled", "pending", "refunded"]},
)

Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="currency", detector_slug="set_membership",
    params={"allowed_values": ["USD", "EUR", "GBP"]},
)

Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="seller_level", detector_slug="set_membership",
    params={"allowed_values": ["level_1", "level_2", "top_rated"]},
)
```

---

### `set_exclusion`
Fraction of values IN a forbidden set. Lower is better.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `forbidden_values` | list | yes | Values that must not appear |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="status", detector_slug="set_exclusion",
    params={"forbidden_values": ["error", "unknown"]},
)
```

---

### `regex_match`
Fraction of values NOT matching a regex pattern. Lower is better.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `pattern` | str | `".*"` | Python regex |

```python
# transaction IDs must start with TXN-
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="transaction_id", detector_slug="regex_match",
    params={"pattern": r"^TXN-\d+$"},
)

# campaign IDs must start with MC-
Check(
    schema_name="public", table_name="marketing_campaigns",
    column_name="campaign_id", detector_slug="regex_match",
    params={"pattern": r"^MC-\d+$"},
)
```

---

### `string_length_range`
Fraction of strings with length outside `[min_len, max_len]`.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_len` | int | `0` | Minimum length (inclusive) |
| `max_len` | int | `255` | Maximum length (inclusive) |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="seller_country", detector_slug="string_length_range",
    params={"min_len": 2, "max_len": 2},  # ISO 2-letter country code
)
```

---

### `string_case_violation`
Fraction of strings that violate the expected case.

| Param | Type | Default | Options |
|-------|------|---------|---------|
| `case` | str | `"upper"` | `"upper"`, `"lower"`, `"title"` |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="currency", detector_slug="string_case_violation",
    params={"case": "upper"},
)
```

---

### `date_format`
Fraction of strings that don't match a date format.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_format` | str | `"%Y-%m-%d"` | strftime pattern |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="date", detector_slug="date_format",
    params={"date_format": "%Y-%m-%d"},
)
```

---

### `freshness_seconds_behind`
Seconds elapsed since the latest timestamp in a column. Declarative — no baseline needed.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `col` | str | `"updated_at"` | Timestamp column name |
| `warn_seconds` | float | `3600` | Warn threshold (1 hour) |
| `fail_seconds` | float | `86400` | Fail threshold (24 hours) |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    detector_slug="freshness_seconds_behind",
    params={
        "col": "date",
        "warn_seconds": 86400,   # warn if > 1 day stale
        "fail_seconds": 172800,  # fail if > 2 days stale
    },
)
```

---

### `monotonicity`
Checks whether a column is monotonically increasing or decreasing. Returns 0.0 (monotonic) or 1.0 (violated).

| Param | Type | Default | Options |
|-------|------|---------|---------|
| `direction` | str | `"increasing"` | `"increasing"`, `"decreasing"` |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="date", detector_slug="monotonicity",
    params={"direction": "increasing"},
)
```

---

### `sql_assertion_violation`
Fraction of rows where a SQL condition is FALSE. Fail ≥ 1%.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `condition` | str | yes | SQL boolean expression (column references are bare names) |

```python
# platform_fee should be ~20% of amount_usd
Check(
    schema_name="public", table_name="gigler_transactions",
    detector_slug="sql_assertion_violation",
    params={"condition": "platform_fee_usd <= amount_usd"},
)

# ROI must be non-negative
Check(
    schema_name="public", table_name="marketing_campaigns",
    detector_slug="sql_assertion_violation",
    params={"condition": "roi >= 0"},
)
```

---

### `column_pair_comparison`
Fraction of rows where a comparison between two columns is false.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `col_a` | str | `"a"` | Left column |
| `col_b` | str | `"b"` | Right column |
| `operator` | str | `">"` | One of `>`, `>=`, `<`, `<=`, `=`, `!=` |

```python
# min_price must be <= max_price
Check(
    schema_name="public", table_name="gig_prices",
    detector_slug="column_pair_comparison",
    params={"col_a": "min_price_usd", "col_b": "max_price_usd", "operator": "<="},
)

# platform_fee must be <= amount_usd
Check(
    schema_name="public", table_name="gigler_transactions",
    detector_slug="column_pair_comparison",
    params={"col_a": "platform_fee_usd", "col_b": "amount_usd", "operator": "<="},
)
```

---

### `composite_uniqueness`
Fraction of duplicate rows across a combination of columns.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `key_columns` | list[str] | yes | Columns that together should be unique |

```python
# (date, gig_category) should be unique in gig_prices
Check(
    schema_name="public", table_name="gig_prices",
    detector_slug="composite_uniqueness",
    params={"key_columns": ["date", "gig_category"]},
)
```

---

### `row_count_in_range`
Declarative: asserts the row count in a date range is between `min_rows` and `max_rows`. No baseline.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date_col` | str | yes | Date/timestamp column |
| `start_date` | str | yes | ISO date |
| `end_date` | str | yes | ISO date |
| `min_rows` | int | no | Minimum expected rows (default: 0) |
| `max_rows` | int | no | Maximum expected rows |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    detector_slug="row_count_in_range",
    params={
        "date_col": "date",
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",
        "min_rows": 10_000,
    },
)
```

---

### `max_in_range` / `min_in_range` / `median_in_range` / `sum_in_range` / `stddev_in_range`
Declarative: asserts an aggregate statistic is within a range.

| Param | Type | Default |
|-------|------|---------|
| `min_val` | float | `0.0` |
| `max_val` | float | `inf` |

```python
# avg_price_usd median should be between $20 and $2000
Check(
    schema_name="public", table_name="gig_prices",
    column_name="avg_price_usd", detector_slug="median_in_range",
    params={"min_val": 20.0, "max_val": 2000.0},
)

# completion_days max should not exceed 90
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="completion_days", detector_slug="max_in_range",
    params={"min_val": 0.0, "max_val": 90.0},
)
```

---

### `cardinality_in_range`
Distinct value count within a range.

```python
# gig_category should have between 10 and 25 distinct values
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="gig_category", detector_slug="cardinality_in_range",
    params={"min_val": 10, "max_val": 25},
)
```

---

### `quantile_in_range`
A specific quantile of a column within a range.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `quantile` | float | yes | 0.0–1.0 |
| `min_val` | float | no | Lower bound |
| `max_val` | float | no | Upper bound |

```python
# 95th percentile of amount_usd should not exceed $5000
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="amount_usd", detector_slug="quantile_in_range",
    params={"quantile": 0.95, "max_val": 5000.0},
)
```

---

### `date_part_missing_fraction`
Fraction of expected date buckets with no data. Detects calendar gaps.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `col` | str | `"created_at"` | Date column |
| `granularity` | str | `"day"` | `"day"`, `"week"`, `"month"`, `"hour"` |
| `lookback_days` | int | `30` | How far back to check |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    detector_slug="date_part_missing_fraction",
    params={"col": "date", "granularity": "day", "lookback_days": 90},
)
```

---

### `referential_integrity_rate`
Fraction of foreign key values that exist in the parent table.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `parent_table` | str | yes | `"schema.table"` |
| `parent_col` | str | no | Parent key column (default: `"id"`) |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="gig_category", detector_slug="referential_integrity_rate",
    params={"parent_table": "public.gig_prices", "parent_col": "gig_category"},
)
```

---

### `schema_change`
Detects column additions, removals, or type changes. Returns 0.0 (no change) or 1.0 (changed).

No `column_name` needed — table-level.

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    detector_slug="schema_change",
)
```

---

## Drift detectors

### `ks_pvalue`
Kolmogorov-Smirnov two-sample test. Compares the distribution of current data against baseline. Score = 1 − p-value. Warn ≥ 0.95 (p < 0.05), fail ≥ 0.99 (p < 0.01).

No params. Requires `fit()` to establish the reference distribution.

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.local import LocalAdapter

df_q1 = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q1.csv")
df_q2 = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q2.csv")

check = Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="amount_usd", detector_slug="ks_pvalue",
)

store = MemoryStore()
runner = Runner(store)
runner.fit(check, LocalAdapter({"public.gigler_transactions": df_q1}))
result = runner.run(check, LocalAdapter({"public.gigler_transactions": df_q2}))
print(result.plain_english)
```

---

## Outlier detectors — univariate

### `mad_outlier_fraction`
Modified Z-score using Median Absolute Deviation (Leys et al. 2013). Robust to skewed distributions — preferred over plain Z-score for financial data like `amount_usd`.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `threshold` | float | `3.5` | Modified Z-score cutoff |

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="amount_usd", detector_slug="mad_outlier_fraction",
    params={"threshold": 3.5},
)
```

---

### `double_mad_outlier_fraction`
Asymmetric MAD (Rousseeuw & Croux 1993). Uses separate MAD thresholds above and below the median. Better than `mad_outlier_fraction` for heavily right-skewed distributions (e.g., `spend_usd`, `revenue_usd`).

| Param | Type | Default |
|-------|------|---------|
| `threshold` | float | `3.5` |

```python
Check(
    schema_name="public", table_name="marketing_campaigns",
    column_name="revenue_usd", detector_slug="double_mad_outlier_fraction",
    params={"threshold": 3.5},
)
```

---

### `zscore_outlier_fraction`
Standard Z-score (mean ± k·σ). Assumes normality. Use `mad_outlier_fraction` instead for financial or long-tailed data.

| Param | Type | Default |
|-------|------|---------|
| `threshold` | float | `3.0` |

```python
Check(
    schema_name="public", table_name="marketing_campaigns",
    column_name="quality_score", detector_slug="zscore_outlier_fraction",
    params={"threshold": 3.0},
)
```

---

### `adjusted_boxplot_fraction`
Tukey fences adjusted for skewness via the medcouple statistic (Hubert & Vandervieren 2008). Best all-round choice for unknown distribution shape.

```python
Check(
    schema_name="public", table_name="gigler_transactions",
    column_name="completion_days", detector_slug="adjusted_boxplot_fraction",
)
```

---

### `auto_outlier_fraction`
Automatically selects among MAD, DoubleMad, ZScore, and AdjustedBoxplot based on the sample's skewness and kurtosis. Use this when you don't know the distribution shape.

```python
Check(
    schema_name="public", table_name="gig_prices",
    column_name="avg_price_usd", detector_slug="auto_outlier_fraction",
)
```

---

## Outlier detectors — multivariate

### `isolation_forest_fraction`
Isolation Forest (Liu et al. 2008). Detects anomalies in the joint distribution across multiple numeric columns. Requires `fit()`.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `contamination` | float | `0.1` | Expected fraction of anomalies |

Table-level check — no `column_name`. The detector uses all numeric columns.

```python
Check(
    schema_name="public", table_name="marketing_campaigns",
    detector_slug="isolation_forest_fraction",
    params={"contamination": 0.05},
)
```

---

## Time series detectors

### `stl_residual_zscore`
Seasonal-Trend decomposition using LOESS (Cleveland et al. 1990). Decomposes the time series into trend + seasonal + residual, then flags anomalies in the residuals. Requires `fit()`.

Score = max absolute Z-score of residuals. Warn ≥ 2.5, fail ≥ 3.5.

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.local import LocalAdapter

df = pd.read_csv("examples/gigler/data/gig_vendor_stats_2024_q1.csv")

check = Check(
    schema_name="public", table_name="gig_vendor_stats",
    column_name="n_active_vendors", detector_slug="stl_residual_zscore",
)

store = MemoryStore()
runner = Runner(store)
result = runner.run(check, LocalAdapter({"public.gig_vendor_stats": df}))
print(result.plain_english)
```

---

## Choosing the right detector

| Scenario | Recommended detector |
|----------|---------------------|
| Column has nulls that shouldn't be there | `null_fraction` |
| Primary key must be unique | `uniqueness` |
| Categorical column with fixed values | `set_membership` |
| Numeric column with hard bounds | `value_in_range` |
| Financial amounts — catch extreme values | `mad_outlier_fraction` |
| Skewed revenue/spend data | `double_mad_outlier_fraction` |
| Unknown distribution shape | `auto_outlier_fraction` or `adjusted_boxplot_fraction` |
| Detect distribution shift across periods | `ks_pvalue` |
| Time series — seasonal anomaly detection | `stl_residual_zscore` |
| Multi-column anomaly detection | `isolation_forest_fraction` |
| Row count drops or spikes | `volume` |
| Table schema changed unexpectedly | `schema_change` |
| FK integrity across tables | `referential_integrity_rate` |
| No data for certain dates | `date_part_missing_fraction` |
| Custom business rule | `sql_assertion_violation` |

# YAML Check Format

dqt checks can be defined in YAML and run with `dqt run`. The format is a strict superset of SodaCL.

## Loading YAML in Python

```python
from dqt.checks.loader import load_checks_yaml, load_checks_file

# from a string
checks = load_checks_yaml(yaml_string)

# from a file
checks = load_checks_file("checks/gigler.yaml")
```

## Complete example — Gigler dataset

```yaml
version: "1"

source:
  type: csv
  id: gigler_local
  path: examples/gigler/data/gigler_transactions_2024_q2.csv
  table_name: gigler_transactions

checks:
  # ── Completeness ──────────────────────────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: null_fraction

  - schema_name: public
    table_name: gigler_transactions
    column_name: transaction_id
    detector_slug: uniqueness

  # ── Value validity ────────────────────────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    column_name: status
    detector_slug: set_membership
    params:
      allowed_values:
        - completed
        - cancelled
        - pending
        - refunded

  - schema_name: public
    table_name: gigler_transactions
    column_name: rating
    detector_slug: value_in_range
    params:
      min_val: 1.0
      max_val: 5.0

  - schema_name: public
    table_name: gigler_transactions
    column_name: seller_level
    detector_slug: set_membership
    params:
      allowed_values:
        - level_1
        - level_2
        - top_rated

  # ── Format checks ─────────────────────────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    column_name: transaction_id
    detector_slug: regex_match
    params:
      pattern: "^TXN-\\d+$"

  - schema_name: public
    table_name: gigler_transactions
    column_name: date
    detector_slug: date_format
    params:
      date_format: "%Y-%m-%d"

  - schema_name: public
    table_name: gigler_transactions
    column_name: seller_country
    detector_slug: string_length_range
    params:
      min_len: 2
      max_len: 2

  # ── Numeric bounds ────────────────────────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    column_name: completion_days
    detector_slug: max_in_range
    params:
      min_val: 0.0
      max_val: 90.0

  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: quantile_in_range
    params:
      quantile: 0.95
      max_val: 5000.0

  # ── Cross-column rules ────────────────────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    detector_slug: column_pair_comparison
    params:
      col_a: platform_fee_usd
      col_b: amount_usd
      operator: "<="

  - schema_name: public
    table_name: gigler_transactions
    detector_slug: sql_assertion_violation
    params:
      condition: "platform_fee_usd >= 0"

  # ── Statistical / baseline-required ──────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: mad_outlier_fraction
    params:
      threshold: 3.5
    baseline:
      window_days: 30
      min_rows: 1000

  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: ks_pvalue
    baseline:
      window_days: 14

  # ── Volume ────────────────────────────────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    detector_slug: volume

  # ── Schema integrity ──────────────────────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    detector_slug: schema_change

  # ── Freshness ─────────────────────────────────────────────────────────────
  - schema_name: public
    table_name: gigler_transactions
    detector_slug: freshness_seconds_behind
    params:
      col: date
      warn_seconds: 86400
      fail_seconds: 172800
```

## Incremental scope

Only check rows added since a cutoff date — useful for large tables.

```yaml
  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: mad_outlier_fraction
    scope:
      mode: incremental
      key_col: date
      since: "2024-04-01"
```

Use `since: "last_run"` to always check only rows newer than the previous run:

```yaml
    scope:
      mode: incremental
      key_col: date
      since: "last_run"
```

## Filters

Filter rows before the detector sees them. Multiple filters are AND'd; values within a filter are OR'd.

```yaml
  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: mad_outlier_fraction
    filters:
      - col: status
        values:
          - completed
      - col: gig_category
        values:
          - AI/ML Development
          - Design & Creative
```

## Sampling

```yaml
  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: ks_pvalue
    sample_n: 50000          # cap at 50k rows

  # or: sample a percentage
    sampling_pct: 10.0       # sample 10% of the table
```

## Multi-table config

```yaml
version: "1"

source:
  type: duckdb
  id: gigler_duckdb
  database: gigler.duckdb

checks:
  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: mad_outlier_fraction

  - schema_name: public
    table_name: gig_prices
    column_name: avg_price_usd
    detector_slug: value_in_range
    params:
      min_val: 5.0
      max_val: 5000.0

  - schema_name: public
    table_name: marketing_campaigns
    column_name: roi
    detector_slug: value_in_range
    params:
      min_val: 0.0

  - schema_name: public
    table_name: gig_vendor_stats
    column_name: avg_vendor_rating
    detector_slug: value_in_range
    params:
      min_val: 1.0
      max_val: 5.0
```

## Source types

| Type | Required fields | Description |
|------|----------------|-------------|
| `csv` | `path`, `table_name` | Single CSV file |
| `parquet` | `path`, `table_name` | Single Parquet file |
| `duckdb` | `database` | DuckDB file |
| `postgres` | `connection_string` | PostgreSQL |

## Full field reference

```yaml
version: "1"                    # always "1"

source:
  type: csv | parquet | duckdb | postgres
  id: string                    # identifier for this source
  path: string                  # for csv/parquet
  table_name: string            # for csv/parquet — the logical table name
  database: string              # for duckdb
  connection_string: string     # for postgres

checks:
  - schema_name: string         # required
    table_name: string          # required
    column_name: string         # optional (omit for table-level detectors)
    detector_slug: string       # required
    params: {}                  # detector-specific params (default: {})
    sample_n: 100000            # max rows to sample (default: 100_000)
    sampling_pct: null          # 0.001–100, overrides sample_n if set
    scope:
      mode: entire | incremental | custom   # default: entire
      key_col: string           # for incremental
      since: string             # ISO date/datetime or "last_run"
      custom_sql: string        # WHERE clause for custom mode
    filters:
      - col: string             # column name
        values: []              # allowed values (OR'd within filter)
    baseline:
      window_days: 14           # reference lookback window (default: 14)
      min_rows: 1000            # minimum rows to fit (default: 1_000)
    schedule: string            # cron schedule (used by server/worker only)
```

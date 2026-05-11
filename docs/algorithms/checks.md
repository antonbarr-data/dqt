# dqt Declarative Checks Catalog

Declarative checks assert hard constraints without needing a statistical baseline. They are the dqt equivalent of Great Expectations expectations and Soda SodaCL checks — YAML-configurable, SodaCL-compatible, and runnable from the CLI or Python API.

All examples use **Gigler** — a fictional gig marketplace.

| Table | Key columns |
|---|---|
| `fct_gigs` | `gig_id`, `seller_id`, `category`, `price_usd`, `created_at`, `status` |
| `fct_bookings` | `booking_id`, `gig_id`, `buyer_id`, `booked_at`, `amount_paid_usd`, `status` |
| `fct_reviews` | `review_id`, `booking_id`, `rating` (1–5), `review_text`, `submitted_at` |
| `dim_sellers` | `seller_id`, `country`, `joined_at`, `tier` (bronze/silver/gold) |

---

## YAML authoring

All checks can be written in YAML (superset of SodaCL) or Python:

```yaml
# checks/fct_gigs.yaml
version: 1
source: gigler_warehouse
dataset: public.fct_gigs
checks:
  - kind: null_fraction
    column: price_usd
    fail_if: "> 0.01"

  - kind: value_in_range
    column: price_usd
    min: 1.0
    max: 50000.0

  - kind: set_membership
    column: status
    values: [active, paused, sold_out, deleted]

  - kind: freshness_seconds_behind
    column: created_at
    fail_if: "> 3600"
```

Run with the CLI:

```bash
dqt run checks/fct_gigs.yaml
```

---

## Python API

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="null_fraction",
    params={"fail_threshold": 0.01},
)
runner = Runner(store=MemoryStore())
result = runner.run(check, adapter)
print(result.verdict, result.plain_english)
```

---

## Nullness & Completeness

| Slug | Description | Doc |
|---|---|---|
| `null_fraction` | Fraction of nulls must stay below threshold | [null_fraction.md](null_fraction.md) |
| `completeness` | Fraction of non-null values must meet minimum | [completeness.md](completeness.md) |
| `date_part_missing_fraction` | Fraction of rows missing a specific date-granularity bucket (day/week/month) | [date_part_missing_fraction.md](date_part_missing_fraction.md) |

```yaml
# Gigler: price_usd must almost never be null
- kind: null_fraction
  column: price_usd
  fail_if: "> 0.001"

# Gigler: created_at must have no missing days in the past 30 days
- kind: date_part_missing_fraction
  column: created_at
  granularity: day
  lookback_days: 30
  fail_if: "> 0.05"
```

---

## Uniqueness & Volume

| Slug | Description | Doc |
|---|---|---|
| `uniqueness` | Fraction of distinct values (or strict all-unique assertion) | [uniqueness.md](uniqueness.md) |
| `composite_uniqueness` | Combination of two or more columns must be unique across the table | [composite_uniqueness.md](composite_uniqueness.md) |
| `volume` | Total row count must fall within expected range | [volume.md](volume.md) |
| `row_count_in_range` | Row count must fall within `[min, max]` with optional date scoping | [row_count_in_range.md](row_count_in_range.md) |

```yaml
# Gigler: gig_id must be unique
- kind: uniqueness
  column: gig_id
  fail_if: "< 1.0"

# Gigler: (gig_id, buyer_id) must be unique in fct_bookings
- kind: composite_uniqueness
  columns: [gig_id, buyer_id]

# Gigler: expect at least 5000 gigs loaded per day
- kind: row_count_in_range
  date_col: created_at
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  min_rows: 5000
  max_rows: 500000
```

---

## Numeric Range Checks

| Slug | Description | Doc |
|---|---|---|
| `numeric_mean` | Column mean must fall within `[min, max]` | [numeric_mean.md](numeric_mean.md) |
| `value_in_range` | Every non-null value must fall within `[min, max]` | [value_in_range.md](value_in_range.md) |
| `min_in_range` | Column minimum must fall within `[min, max]` | [min_in_range.md](min_in_range.md) |
| `max_in_range` | Column maximum must fall within `[min, max]` | [max_in_range.md](max_in_range.md) |
| `median_in_range` | Column median must fall within `[min, max]` | [median_in_range.md](median_in_range.md) |
| `sum_in_range` | Column sum must fall within `[min, max]` | [sum_in_range.md](sum_in_range.md) |
| `stddev_in_range` | Column standard deviation must fall within `[min, max]` | [stddev_in_range.md](stddev_in_range.md) |
| `cardinality_in_range` | Number of distinct values must fall within `[min, max]` | [cardinality_in_range.md](cardinality_in_range.md) |
| `quantile_in_range` | A given quantile (e.g. p95) must fall within `[min, max]` | [quantile_in_range.md](quantile_in_range.md) |

```yaml
# Gigler: gig prices must be between $1 and $50,000
- kind: value_in_range
  column: price_usd
  min: 1.0
  max: 50000.0

# Gigler: average booking amount should not exceed $10,000
- kind: numeric_mean
  column: amount_paid_usd
  max: 10000.0

# Gigler: p99 of delivery_days must be < 60
- kind: quantile_in_range
  column: delivery_days
  quantile: 0.99
  max: 60
```

---

## Categorical & String Checks

| Slug | Description | Doc |
|---|---|---|
| `set_membership` | Every non-null value must appear in an allowed set | [set_membership.md](set_membership.md) |
| `set_exclusion` | Every non-null value must not appear in a forbidden set | [set_exclusion.md](set_exclusion.md) |
| `regex_match` | Fraction of values matching a regex pattern must meet threshold | [regex_match.md](regex_match.md) |
| `string_length_range` | String length of every value must fall within `[min_len, max_len]` | [string_length_range.md](string_length_range.md) |
| `string_case_violation` | Fraction of values violating the expected case rule (upper/lower/title) | [string_case_violation.md](string_case_violation.md) |
| `date_format` | Every value must parse against a strftime format string | [date_format.md](date_format.md) |
| `validity` | Composite validity rule: column passes when a specified fraction of values satisfy all sub-checks | [validity.md](validity.md) |

```yaml
# Gigler: seller tier must be one of three values
- kind: set_membership
  column: tier
  values: [bronze, silver, gold]

# Gigler: email column must match email pattern
- kind: regex_match
  column: email
  pattern: "^[^@]+@[^@]+\\.[^@]+$"
  fail_if: "< 0.99"

# Gigler: status must be stored lowercase
- kind: string_case_violation
  column: status
  case: lower
  fail_if: "> 0"

# Gigler: created_at stored as a date string
- kind: date_format
  column: created_at
  date_format: "%Y-%m-%d"
  fail_if: "> 0"
```

---

## Relational Checks

| Slug | Description | Doc |
|---|---|---|
| `column_pair_comparison` | Two columns in the same row must satisfy a comparison operator | [column_pair_comparison.md](column_pair_comparison.md) |
| `monotonicity` | Values in a column must be non-decreasing (or non-increasing) | [monotonicity.md](monotonicity.md) |

```yaml
# Gigler: booking amount must not exceed listed gig price + 20%
- kind: column_pair_comparison
  col_a: amount_paid_usd
  col_b: max_allowed_amount
  operator: "<="
  fail_if: "> 0"

# Gigler: cumulative bookings column must be non-decreasing
- kind: monotonicity
  column: cumulative_bookings
  direction: increasing
```

---

## Freshness

| Slug | Description | Doc |
|---|---|---|
| `freshness_seconds_behind` | Timestamp column must be no more than N seconds behind wall clock | [freshness_seconds_behind.md](freshness_seconds_behind.md) |

```yaml
# Gigler: fct_bookings must have data no more than 1 hour old
- kind: freshness_seconds_behind
  col: booked_at
  warn_seconds: 1800   # warn at 30 min
  fail_seconds: 3600   # fail at 1 hour
```

---

## Schema

| Slug | Description | Doc |
|---|---|---|
| `schema_change` | Detects added, removed, or type-changed columns relative to a recorded schema snapshot | [schema_change.md](schema_change.md) |

```yaml
# Gigler: alert if any column is dropped or changes type in fct_bookings
- kind: schema_change
  fail_on: [removed, type_changed]
  warn_on: [added]
```

---

## Referential Integrity

| Slug | Description | Doc |
|---|---|---|
| `referential_integrity_rate` | Fraction of foreign-key values that exist in the parent table's primary key | [referential_integrity_rate.md](referential_integrity_rate.md) |

```yaml
# Gigler: all booking.gig_id values must exist in fct_gigs
- kind: referential_integrity_rate
  child_column: gig_id
  parent_table: public.fct_gigs
  parent_column: gig_id
  fail_if: "< 0.999"
```

---

## Custom SQL

| Slug | Description | Doc |
|---|---|---|
| `sql_assertion_violation` | Fraction of rows returned by a custom SQL query must be below threshold (each returned row = one violation) | [sql_assertion_violation.md](sql_assertion_violation.md) |

```yaml
# Gigler: booking amount must match gig price (within rounding)
- kind: sql_assertion_violation
  name: booking_amount_matches_gig_price
  condition: "amount_paid_usd > price_usd * 1.001"
  fail_if: "> 0"
```

```python
# Python API equivalent
from dqt.algorithms.basic.sql_assertion import SQLAssertionDetector

det = SQLAssertionDetector(condition="price_usd > 0")
result = det.score(df, det.fit(df))
print(result.plain_english)
# → "0 violations found — all 10,000 rows satisfy price_usd > 0"
```

---

## Quick Reference

All 29 check slugs by group:

```
nullness:        null_fraction · completeness · date_part_missing_fraction

uniqueness:      uniqueness · composite_uniqueness · volume · row_count_in_range

numeric:         numeric_mean · value_in_range · min_in_range · max_in_range
                 median_in_range · sum_in_range · stddev_in_range
                 cardinality_in_range · quantile_in_range

categorical:     set_membership · set_exclusion · regex_match
                 string_length_range · string_case_violation · date_format · validity

relational:      column_pair_comparison · monotonicity

freshness:       freshness_seconds_behind

schema:          schema_change

referential:     referential_integrity_rate

custom_sql:      sql_assertion_violation
```

→ Full statistical detector catalog: [detectors.md](detectors.md)
→ Master entry point (all 64 slugs with examples): [README.md](README.md)

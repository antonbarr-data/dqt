# `basic.sql_assertion_violation`

> *SQL assertion violation* — fraction of rows failing a custom SQL condition.

## What it checks

Evaluates `NOT (condition)` for each row and returns the fraction of violations. The `condition` is a trusted SQL boolean expression provided at check-definition time (not at runtime). A score of 0.0 means all rows satisfy the condition. This is the escape hatch for any rule not covered by the other declarative checks. The condition is embedded directly into the aggregation SQL so it has access to all columns in the table.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `condition` | `str` | *(required)* | SQL boolean expression that should be true for every valid row (e.g. `amount > 0 AND status IS NOT NULL`) |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% violations) |
| fail | 0.01 (1% violations) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.sql_assertion import SqlAssertionDetector

# Gigler: every booking must have a positive amount, known status, and a valid buyer
det = SqlAssertionDetector(
    condition="amount_paid_usd > 0 AND status IS NOT NULL AND buyer_id IS NOT NULL",
    # Write the condition that should be TRUE for every valid row.
    # Rows where the condition is FALSE are violations (score = violation fraction).
    # Can reference any column in the table — no single-column restriction.
    # Must be valid SQL for your warehouse engine (standard SQL works everywhere).
)

check = Check(
    schema_name="public",
    table_name="fct_bookings",
    detector_slug="sql_assertion_violation",
    params={"condition": "amount_paid_usd > 0 AND status IS NOT NULL AND buyer_id IS NOT NULL"},
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.plain_english)
# → "0/48231 rows fail: amount_paid_usd > 0 AND status IS NOT NULL AND buyer_id IS NOT NULL"
```

### More examples

```python
# Cross-column business rule: booking amount must not exceed 120% of the gig's listed price
SqlAssertionDetector(condition="amount_paid_usd <= price_usd * 1.20")

# Referential sanity without a JOIN: gig_id must be a positive integer
SqlAssertionDetector(condition="gig_id > 0 AND gig_id IS NOT NULL")

# Date ordering: booking must happen after the gig was created
SqlAssertionDetector(condition="booked_at >= gig_created_at")
```

### YAML equivalent

```yaml
checks:
  - kind: sql_assertion_violation
    table: public.fct_bookings
    condition: "amount_paid_usd > 0 AND status IS NOT NULL AND buyer_id IS NOT NULL"
    fail_if: "> 0"        # zero tolerance for this rule
```

## Compatible with

- Great Expectations: `expect_column_pair_values_to_be_equal` (partial); use `SqlAlchemyDataset` for custom SQL
- Soda: `failed_rows` (with custom SQL)
- Dataplex: `SqlAssertion` rule

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/sql_assertion.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/sql_assertion.py)

## When it works well

- Complex business rules that require arbitrary SQL (multi-table joins, window functions, CTEs) and cannot be expressed with single-column checks.
- The SQL returns a count of failing rows; the violation fraction is this count divided by total rows.

## When it fails / Limitations

- User-supplied SQL — errors in the SQL produce `DetectorError`; always validate the assertion query against the warehouse before deploying.
- Performance depends entirely on the SQL complexity; avoid full-table scans in critical-path checks.
- Not portable across warehouse engines without SQL dialect adjustments; use ibis expressions or parameterised checks for multi-engine portability.
- FPR at defaults: 0% (rule-based — the SQL defines the rule exactly).
- Minimum recommended sample: as required by the SQL logic.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Hard business rule | (default) | (default) | STAT_SCALES defaults |
| Soft tolerance | 0.001 | 0.01 | Allow small violation fraction |
| Statistical assertion | calibrate | calibrate | Calibrate against reference data |

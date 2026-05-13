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

## Failure modes and known limits

`sql_assertion_violation` executes user-supplied SQL, so correctness depends entirely on the SQL expression provided. The detector adds no statistical machinery; it embeds the condition directly into an aggregation query. The main risks are incorrect SQL logic, dialect portability, and performance.

| Failure mode | Symptom | Fix |
|---|---|---|
| NULL propagation in SQL | `amount > 0` returns NULL (not FALSE) when amount is NULL; NULL rows are not counted as violations | Use explicit null handling: `amount IS NOT NULL AND amount > 0`; or test separately with `null_fraction` |
| SQL dialect incompatibility | A condition using DATEADD or MySQL-specific functions fails on Postgres | Write standard SQL or use warehouse-specific conditions only after testing on all target engines |
| Full-table scan in condition | A subquery (e.g. `NOT EXISTS (SELECT ...)`) causes a full-table scan on every run | Pre-aggregate the subquery result into a summary table; or use `referential_integrity_rate` for referential checks |
| Division by zero in condition | `amount / quantity` fails when quantity = 0 | Use `NULLIF(quantity, 0)` to avoid division by zero in the condition |
| Condition changed after incident investigation | Condition was loosened to stop the alert; the underlying issue was not fixed | Track condition changes in the audit log; require HITL approval for condition weakening |
| Score direction confusion | Violation fraction is `lower_is_better`; a score of 0.01 means 1% of rows fail | Ensure alerting is configured for lower_is_better; the score is NOT a pass probability |

### FPR table

| SQL condition type | Expected FPR | Notes |
|---|---|---|
| Deterministic boolean (no statistical approximation) | 0% | FPR is fully determined by the correctness of the SQL |
| Condition involving statistical functions (e.g. STDDEV) | Depends on the function's sampling distribution | Document which statistical assumptions the SQL makes |

### Threshold recommendations

- For zero-tolerance business rules (no nulls in a key column, price always positive): set `fail_if: "> 0"` in YAML (fail on any violation).
- For rules with expected edge cases: measure the historical baseline violation rate and set warn at 2x baseline.
- Always validate the SQL against the target warehouse with a test query before deploying the check.

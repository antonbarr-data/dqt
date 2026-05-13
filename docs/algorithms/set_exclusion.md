# `basic.set_exclusion`

> *Set exclusion* — fraction of values that appear in the forbidden set.

## What it checks

Evaluates `col IN (forbidden_values)` for each row and returns the fraction of violations. A score of 0.0 means no values match the forbidden set. Useful for blocking known-bad sentinel values (e.g. `"N/A"`, `"test"`, `"null"`), deprecated enum members, or PII indicator strings.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `forbidden_values` | `list` or `set` | *(required, non-empty)* | Values that must not appear in the column |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% violations) |
| fail | 0.01 (1% violations) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.value_checks import SetExclusionDetector

det = SetExclusionDetector(
    forbidden_values=["banned", "spam"],
    # list values that must never appear; useful for sentinel values
    # that should be filtered upstream (e.g. "NULL" as a string, "test", "DELETE").
    # score = fraction of non-null values that ARE in the forbidden set.
)

check = Check(
    schema_name="public",
    table_name="users",
    column_name="email",
    detector_slug="set_exclusion",
    params={"forbidden_values": ["test@example.com", "noreply@example.com"]},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_not_be_in_set`
- Soda: `invalid_values`

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/value_checks.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/value_checks.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`

## When it works well

- Categorical columns where certain values are never allowed (blocked country codes, deprecated status values, test environment markers).
- Zero false positives on clean data — a pure deterministic rule.

## When it fails / Limitations

- The excluded set must be explicitly maintained; new prohibited values must be added manually.
- Does not catch values outside the excluded set that are still invalid — combine with `set_membership` for a complete allowlist/blocklist approach.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Categorical with explicit blocklist | (default) | (default) | STAT_SCALES defaults |
| High-cardinality columns | N/A | N/A | Maintain blocklist carefully |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

`set_exclusion` is a pure membership test: FPR is 0% if the forbidden set is correctly specified. All practical failure modes come from blocklist maintenance - values that should be forbidden but are not in the list, or values that were added by mistake.

| Failure mode | Symptom | Fix |
|---|---|---|
| Stale blocklist (new bad values not added) | New sentinel values (e.g. "N/A", "UNKNOWN") enter the table and are not caught | Audit the distinct value set quarterly; trigger a re-review when `cardinality_in_range` detects new categories |
| Case sensitivity mismatch | "test" is forbidden but "TEST" or "Test" passes | Add all case variants to the forbidden set, or normalize case upstream |
| Whitespace variants | "banned " (trailing space) is not caught by "banned" | Trim values upstream; add TRIM() in a `sql_assertion_violation` if the column contains whitespace variants |
| Null is forbidden but passes | Null values are not matched by `IN (...)` in SQL - they are excluded from the violation count | Use `null_fraction` to catch nulls if they are also forbidden |
| Blocklist too large (> 1000 values) | Performance degrades on very large IN lists on some warehouses | Switch to a separate blocklist table and use `sql_assertion_violation` with a NOT EXISTS join |

### FPR table

| Scenario | Expected FPR | Notes |
|---|---|---|
| Stable blocklist on stable categorical | 0% | Fully deterministic |
| After schema evolution introduces new categories | 0% (but false negatives rise) | New bad values not in the list are missed |

### Threshold recommendations

- Default warn=0.001 / fail=0.01 is appropriate for most categorical columns.
- For PII or compliance blocklists (e.g. test emails, known-bad account IDs): set fail=0 via `fail_if: "> 0"`.
- For large blocklists: implement the check as a `sql_assertion_violation` with a LEFT JOIN to a blocklist table rather than a large IN list.

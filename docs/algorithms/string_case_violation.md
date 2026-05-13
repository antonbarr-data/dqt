# `basic.string_case_violation`

> *String case violation* — fraction of non-null rows where the string does not match the expected case.

## What it checks

For each non-null value, checks whether `col = UPPER(col)` (upper), `col = LOWER(col)` (lower), or `col = INITCAP(col)` (title case). Returns the fraction of non-null rows that violate the rule. A score of 0.0 means all non-null values have the correct casing.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `case` | `str` | `"upper"` | Expected casing: `"upper"`, `"lower"`, or `"title"` |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% violations) |
| fail | 0.01 (1% violations) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.string_case import StringCaseViolationDetector

det = StringCaseViolationDetector(
    case="upper",
    # "lower" for snake_case column values (status, category).
    # "upper" for codes and identifiers (ISO codes, ENUM values).
    # "title" for display names.
    # score = fraction of non-null values violating the rule.
)

check = Check(
    schema_name="public",
    table_name="countries",
    column_name="country_code",
    detector_slug="string_case_violation",
    params={"case": "upper"},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_match_regex` (with case regex)
- Soda: no direct equivalent

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/string_case.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/string_case.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/string_case.py`

## When it works well

- String columns with a strict casing convention (UPPER for codes, lower for emails, Title for names).
- Zero false positives on clean data — a deterministic rule.

## When it fails / Limitations

- Mixed-case columns (proper nouns, product names with abbreviations) require careful configuration or will produce constant false positives.
- Does not normalise case — it only detects violations, not fixes them.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Strict casing required | (default) | (default) | STAT_SCALES defaults |
| Mixed-case column | N/A | N/A | Not applicable |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

`string_case_violation` is a deterministic rule: FPR is 0% for clean data. False positives come from misspecified case expectations (e.g. expecting UPPER on a column that legitimately contains mixed-case product names). False negatives are impossible (the check evaluates every row).

| Failure mode | Symptom | Fix |
|---|---|---|
| Column has legitimate mixed case | Product names, proper nouns, or abbreviations (e.g. "iPhone", "NASA") fail an UPPER check | Do not use `string_case_violation` on free-text or proper-noun columns |
| Source system changed casing convention | An upstream system switched from UPPER to lower for status codes; sudden spike in violations | Investigate the upstream change; standardise at ingest |
| Locale-dependent case mapping | UPPER("i") in Turkish locale produces "I" (dotted I); differs from English UPPER | Ensure warehouse collation is set consistently for the column |
| Title case check on names with prepositions | INITCAP("de la Rosa") produces "De La Rosa" which fails `title` expectation | Use `sql_assertion_violation` with a custom INITCAP-exempt list for known multi-word names |
| Numeric or non-alphabetic values | Numeric strings and symbols have no case; UPPER(col) = LOWER(col) = col; check always passes | The check correctly treats non-alphabetic values as case-conformant; this is the expected behaviour |

### FPR table

| Scenario | Expected FPR | Notes |
|---|---|---|
| Single-case strict column (ISO codes, enums) | 0% | Fully deterministic |
| Column with known exceptions (abbreviations) | Proportional to exception fraction | Filter known exceptions via `sql_assertion_violation` |

### Threshold recommendations

- Default warn=0.001 / fail=0.01 is appropriate for strict format columns (country codes, status values).
- For zero-tolerance casing (e.g. column feeds a case-sensitive downstream system): set `fail_if: "> 0"` in YAML.
- Do not deploy this check on free-text or user-input columns without first auditing the expected casing distribution.

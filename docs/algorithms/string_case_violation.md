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

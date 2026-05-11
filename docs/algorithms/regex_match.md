# `basic.regex_match`

> *Regex format* — fraction of values that do not match the regular expression pattern.

## What it checks

Evaluates `col::text !~ pattern` (Postgres `~` operator, case-sensitive POSIX regex) for each row and returns the fraction of violations. A score of 0.0 means all non-null values match the pattern. Null values are counted as violations. Single quotes in the pattern are escaped automatically.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pattern` | `str` | `".*"` | POSIX regular expression that valid values must match |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% violations) |
| fail | 0.01 (1% violations) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="users",
    column_name="phone",
    detector_slug="regex_match",
    params={"pattern": r"^\+?[0-9\-\s]{7,15}$"},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_match_regex`
- Soda: `valid_format` / `valid_regex`

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`

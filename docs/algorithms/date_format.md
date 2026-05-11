# `basic.date_format`

> *Date format* — fraction of non-null values whose string representation does not match the expected date format.

## What it checks

Converts the declared format string to a structural POSIX regex (e.g. `%Y-%m-%d` → `^\d{4}-\d{2}-\d{2}$`) and evaluates `col::text !~ regex` for each non-null row. Returns the fraction of violations. This is a structural check — it validates the shape of the string, not calendar validity. For calendar-valid date checks use `sql_assertion_violation` with a cast predicate.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_format` | `str` | `"%Y-%m-%d"` | Expected format using `strptime` tokens (`%Y`, `%m`, `%d`, `%H`, `%M`, `%S`) or SQL tokens (`YYYY`, `MM`, `DD`, `HH24`, `MI`, `SS`) |

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
    table_name="events",
    column_name="event_date",
    detector_slug="date_format",
    params={"date_format": "%Y-%m-%d"},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_match_strftime_format`
- Soda: `valid_format` (date variant)

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`

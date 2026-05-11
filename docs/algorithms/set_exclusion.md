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

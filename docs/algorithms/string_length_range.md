# `basic.string_length_range`

> *String length* — fraction of values whose character length falls outside `[min_len, max_len]`.

## What it checks

Evaluates `LENGTH(col::text) < min_len OR LENGTH(col::text) > max_len` for each row and returns the fraction of violations. A score of 0.0 means all values have acceptable length. Null values count as violations. Works on any column type cast to text.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_len` | `int` | `0` | Minimum acceptable character length (inclusive) |
| `max_len` | `int` | `255` | Maximum acceptable character length (inclusive) |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% violations) |
| fail | 0.01 (1% violations) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.value_checks import StringLengthRangeDetector

det = StringLengthRangeDetector(
    min_len=3,   # set min_len=1 to reject empty strings;
                 # for email addresses use min_len=6 (RFC 5321 lower bound).
    max_len=32,  # for email addresses use max_len=254 (RFC 5321 limit);
                 # for short codes (ISO country codes) use max_len=3.
    # score = fraction of non-null values with length outside [min_len, max_len].
)

check = Check(
    schema_name="public",
    table_name="users",
    column_name="username",
    detector_slug="string_length_range",
    params={"min_len": 3, "max_len": 32},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_value_lengths_to_be_between`
- Soda: `min_length` / `max_length`

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/value_checks.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/value_checks.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`

## When it works well

- String columns with known length constraints (SSN, postal codes, product codes, fixed-length identifiers).
- Zero false positives on clean data that satisfies the constraint — a deterministic rule.

## When it fails / Limitations

- Variable-length free text columns (comments, descriptions) — length range is hard to define without producing false positives.
- Requires calibration of min/max bounds; too-tight bounds fire on legitimate edge-case values.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Fixed-length identifier | exact min=max | exact min=max | Strict equality on length |
| Variable-length with bounds | (default) | (default) | STAT_SCALES defaults |
| Free text | N/A | N/A | Not appropriate for this check |

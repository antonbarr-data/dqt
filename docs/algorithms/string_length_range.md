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

## Failure modes and known limits

`string_length_range` measures character length (not byte length). This distinction matters for multibyte encodings (UTF-8 CJK characters, emoji). Most warehouses implement `LENGTH()` as character length, but some use byte length. Verify behaviour on your warehouse before deploying for non-ASCII columns.

| Failure mode | Symptom | Fix |
|---|---|---|
| Multibyte character length vs byte length | A 3-character CJK string may be 9 bytes; LENGTH() may return 9 not 3 on some warehouses | Test with a known multibyte value; use CHAR_LENGTH() explicitly if the warehouse supports it |
| Null values counted as violations | NULL strings fail the length check if null_handling=count_as_violation | Use `null_fraction` separately; set `null_handling=exclude` on the check |
| Trailing spaces inflate length | "USA   " has length 6, not 3; upstream ETL did not TRIM | Trim whitespace at ingest; add TRIM() in a `sql_assertion_violation` if columns are known to contain trailing spaces |
| Bounds too tight for edge-case valid values | A username with exactly 2 characters is legitimate but min_len=3 rejects it | Review real-world edge cases before setting min_len |
| Column type is not text | A numeric column cast to text may produce strings of variable length (e.g. "1" vs "1000") | Check whether the cast-to-text representation is stable; avoid using string_length_range on numeric columns |

### FPR table

| Scenario | Expected FPR | Notes |
|---|---|---|
| Fixed-length identifier (e.g. ISO-2 country code) | 0% | Correct bounds produce zero FPR |
| Variable-length column with 30-day calibrated bounds | ~0% | Bounds derived from historical range eliminate FPR |

### Threshold recommendations

- For fixed-length identifiers (SSN, IBAN, country code): set min_len=max_len=expected_length with `fail_if: "> 0"`.
- For variable-length columns: derive min_len from the 0.1st percentile and max_len from the 99.9th percentile of historical lengths.
- For free-text columns (descriptions, comments): do not use this check; length variation is expected and meaningful.

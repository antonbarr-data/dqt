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
from dqt.algorithms.basic.value_checks import RegexMatchDetector

det = RegexMatchDetector(
    pattern=r"^\+?[0-9\-\s]{7,15}$",
    # Python re pattern; anchor with ^ and $ for full-string matching.
    # for emails use r"^[^@]+@[^@]+\.[^@]+$"
    # for UUIDs use r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    # score = fraction of non-null values NOT matching (0 = all match = good).
)

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

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/value_checks.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/value_checks.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`

## When it works well

- String columns with a known format (email addresses, phone numbers, ISO codes, UUIDs, postal codes).
- Zero false positives on clean data — a deterministic pattern match.

## When it fails / Limitations

- Regex complexity grows with format variations — overly strict patterns produce false positives on legitimate variations (e.g. international phone number formats).
- Does not validate semantic correctness, only format — a syntactically valid email may not exist.
- Performance degrades with complex regexes on very wide text columns (> 10,000 characters).
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Strict format column | (default) | (default) | STAT_SCALES defaults |
| Flexible format column | 0.01 | 0.05 | Allow small fraction of format variations |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

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

## Failure modes and known limits

`regex_match` evaluates a POSIX regex against each value's text representation. FPR is 0% for clean data that genuinely matches the pattern. False positives come from patterns that are too strict for the actual data; false negatives come from patterns that are too permissive.

| Failure mode | Symptom | Fix |
|---|---|---|
| Pattern too strict for international data | International phone numbers, addresses, or names have formats the pattern does not cover | Test the pattern against a representative international sample before deploying |
| Null counted as violation | Null values fail the regex match and inflate the violation rate | Use `null_fraction` separately; set `null_handling=exclude` on the check definition |
| Regex catastrophic backtracking | A complex pattern on a wide text column causes warehouse query timeout | Avoid nested quantifiers in the pattern; test with `EXPLAIN` before deploying |
| Warehouse POSIX vs Python regex dialect | The pattern uses Python-only syntax (e.g. `(?P<name>...)`) which is not valid POSIX | Use only POSIX ERE syntax; test against your target warehouse regex engine |
| Case sensitivity | Pattern is case-sensitive (default) but data has mixed case | Add `(?i)` flag or use `ILIKE` in a `sql_assertion_violation` instead |
| Unicode characters in value | Non-ASCII characters in the column may match or fail unexpectedly depending on warehouse collation | Test with representative Unicode samples; use `sql_assertion_violation` with explicit collation if needed |

### FPR table

| Scenario | Expected FPR | Notes |
|---|---|---|
| Correct pattern on single-format column | 0% | Fully deterministic |
| Pattern misses 1% of legitimate formats | ~1% false positives | Every legitimate non-matching format contributes to FPR |

### Threshold recommendations

- Default warn=0.001 / fail=0.01 is appropriate for well-defined format columns.
- For formats with legitimate variation (e.g. phone numbers with or without country code): calibrate from a 30-day historical violation rate and set warn at 2x the baseline rate.
- Always anchor patterns with `^` and `$` to avoid partial matches that miss invalid prefixes or suffixes.

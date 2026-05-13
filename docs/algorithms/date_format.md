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
from dqt.algorithms.basic.value_checks import DateFormatDetector

det = DateFormatDetector(
    date_format="%Y-%m-%d",
    # use Python strftime format strings.
    # "%Y-%m-%d" for ISO dates (most common).
    # "%Y-%m-%dT%H:%M:%S" for ISO datetimes.
    # "%d/%m/%Y" for EU format.
    # score = fraction of non-null values that do NOT parse against the format.
)

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

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/value_checks.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/value_checks.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`

## When it works well

- Date/timestamp string columns where the format must conform to a specific pattern (ISO 8601, US MM/DD/YYYY, etc.).
- Zero false positives on clean data — a deterministic format check.

## When it fails / Limitations

- Multiple valid formats in the same column (e.g. dates sourced from different systems) — will flag the minority format as violations.
- Does not validate that the date values are semantically correct (e.g. 2024-02-30 passes format check but is invalid).
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Single strict format | (default) | (default) | STAT_SCALES defaults |
| Multi-format column | N/A | N/A | Standardise upstream first |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

`date_format` is a structural pattern check, not a calendar-validity check. It validates the shape of the string (digit counts, separators), not whether the date is a real calendar date. FPR on clean data is 0%. False positives come from legitimate format variation (e.g. both `YYYY-MM-DD` and `YYYY-M-D` in the same column). False negatives come from dates that match the pattern structurally but are semantically invalid (e.g. `2024-02-30`).

| Failure mode | Symptom | Fix |
|---|---|---|
| Mixed format source systems | Minority format fires as violations (e.g. 5% of rows use MM/DD/YYYY while the rest use YYYY-MM-DD) | Standardise at ingest; if mixed is expected, use `sql_assertion_violation` with a CASE WHEN per format |
| Timezone suffix not in pattern | `2024-01-15T10:30:00Z` fails `%Y-%m-%dT%H:%M:%S` because of the trailing `Z` | Include the suffix in the pattern or strip it upstream |
| Single-digit month/day padding | `2024-1-5` fails `%Y-%m-%d` because it expects zero-padded month | Use `%Y-%-m-%-d` (platform-specific) or normalise to zero-padded form upstream |
| Column stored as date/timestamp type | The adapter casts to text before checking; casting format varies by warehouse (e.g. Postgres uses ISO 8601, BigQuery uses a different default) | Test the cast output format in your specific warehouse before setting the format string |
| Null counted as violation | Score numerator includes null rows; null fraction appears inside format violation rate | Use `null_fraction` separately; set `null_handling=exclude` on the check definition |

### FPR table

| Data shape | Expected FPR | Notes |
|---|---|---|
| Uniform single-format column | 0% | Fully deterministic |
| Column with locale-dependent separators | 0% (if pattern matches) or 100% (if pattern doesn't match) | FPR is binary for structural checks |

### Threshold recommendations

- Default warn=0.001 / fail=0.01 is appropriate for columns with a single enforced format.
- For columns that accept a small proportion of legacy formats, calibrate from the historical violation rate and set warn at 2x the baseline.
- For zero-tolerance format columns (date keys, partition columns), set fail=0 via `fail_if: "> 0"` in YAML.

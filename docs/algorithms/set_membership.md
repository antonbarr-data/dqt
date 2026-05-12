# `basic.set_membership`

> *Set membership* — fraction of values not in the allowed set.

## What it checks

Evaluates `col NOT IN (allowed_values)` for each row and returns the fraction of violations. A score of 0.0 means all values are members of the allowed set. Null values count as violations (not in the set). The allowed set is quoted as string literals in the SQL; cast to the column type as needed.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allowed_values` | `list` or `set` | *(required, non-empty)* | The complete set of permitted values |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% violations) |
| fail | 0.01 (1% violations) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.value_checks import SetMembershipDetector

det = SetMembershipDetector(
    allowed_values=["pending", "paid", "shipped", "cancelled"],
    # list every valid category value; be exhaustive —
    # any value not in this list counts as a violation.
    # use a frozenset for large allowed sets (faster lookup).
    # score = fraction of non-null values NOT in the set (0 = all match = good).
)

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="status",
    detector_slug="set_membership",
    params={"allowed_values": ["pending", "paid", "shipped", "cancelled"]},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_be_in_set`
- Soda: `valid_values`

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/value_checks.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/value_checks.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`

## When it works well

- Categorical columns with a known, fixed allowed-values set (status codes, enum columns, country ISO codes).
- Zero false positives on clean data — a pure deterministic rule.

## When it fails / Limitations

- Allowed-values set that is not stable over time (e.g. new product categories being added) — requires the set to be updated; otherwise fires on legitimate new values.
- High-cardinality columns where maintaining a complete allowed set is impractical; use `regex_match` or a semantic check instead.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Enum / status column | (default) | (default) | STAT_SCALES defaults |
| Evolving allowed set | N/A | N/A | Keep set updated or use regex_match |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

# `schema.schema_change`

> *Schema change* — 1.0 if the table schema has changed since baseline; 0.0 if unchanged.

## What it checks

On `fit()`, records the current schema as a `{col_name: data_type}` mapping from `describe_columns()`. On each run, compares the current schema to the baseline and reports any columns added, removed, or whose type has changed. Returns 0.0 only when the schema is identical to baseline. Any difference results in a score of 1.0 and a `fail` verdict with a detailed breakdown of what changed.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Baseline schema is captured automatically by `fit()` |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.5 |
| fail | 0.5 |
| direction | lower_is_better |

The warn and fail thresholds are both 0.5, so any schema change (score = 1.0) is immediately a fail.

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="schema_change",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
# print(result.details)   # {"added": [...], "removed": [...], "type_changed": [...]}
```

## Compatible with

- Great Expectations: `expect_table_columns_to_match_ordered_list` (partial)
- Soda: `schema` checks
- Elementary: `schema_changes`

## Source

`packages/dqt/src/dqt/algorithms/schema/schema_checks.py`

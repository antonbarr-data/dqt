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
from dqt.algorithms.schema.schema_checks import SchemaChangeDetector

det = SchemaChangeDetector()
# no params; fit() records the current schema (col_name → data_type mapping).
# score() compares against the snapshot and returns score=0 (pass) or score=1 (fail)
# with details listing added, removed, and type-changed columns.

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

## Implementation

[`packages/dqt/src/dqt/algorithms/schema/schema_checks.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/schema/schema_checks.py)

## Source

`packages/dqt/src/dqt/algorithms/schema/schema_checks.py`

## When it works well

- Any table where the schema (column names, types, nullability, ordering) is expected to be stable.
- Catches accidental upstream schema changes (column renames, type promotions, dropped columns) before they break downstream queries.

## When it fails / Limitations

- Tables with intentionally evolving schemas (frequent DDL changes) require a tolerant mode (detect only removals/type conflicts, not additions).
- Does not detect semantic schema changes (e.g. column meaning changes but name and type stay the same).
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: N/A (schema check, not a data sample check).
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Stable schema | (default) | (default) | STAT_SCALES defaults |
| Additive-only evolution | additions=warn | removals=fail | Configure mode per table |
| Frequent schema changes | N/A | N/A | Consider skipping or using custom policy |

# `basic.row_count_in_range`

> *Row count in range* — 1.0 if the row count in a date window falls outside `[min_rows, max_rows]`; 0.0 otherwise.

## What it checks

Counts rows where `date_col` falls within `[start_date, end_date]` and tests whether the count is within the declared bounds. Returns a binary score: 0.0 (pass) if count is in range, 1.0 (fail) otherwise. No baseline is needed — bounds are declared explicitly. Useful for SLA checks like "fct_orders must have 50–500 rows per day".

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_col` | `str` | *(required)* | Date or timestamp column to filter on |
| `start_date` | `str` | *(required)* | Window start (inclusive), ISO format |
| `end_date` | `str` | *(required)* | Window end (inclusive), ISO format |
| `min_rows` | `int` | `0` | Minimum acceptable row count |
| `max_rows` | `int` | `2^31` | Maximum acceptable row count |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.5 |
| fail | 0.5 |
| direction | lower_is_better |

The warn and fail thresholds are both 0.5, so any violation (score = 1.0) is immediately a fail.

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="row_count_in_range",
    params={
        "date_col": "created_at",
        "start_date": "2024-01-01",
        "end_date": "2024-01-01",
        "min_rows": 50,
        "max_rows": 500,
    },
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_table_row_count_to_be_between`
- Soda: `row_count` (with threshold)

## Source

`packages/dqt/src/dqt/algorithms/basic/volume.py`

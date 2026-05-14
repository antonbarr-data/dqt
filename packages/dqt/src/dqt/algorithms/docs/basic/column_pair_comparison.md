# Column-pair comparison (`column_pair_comparison`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Evaluates `NOT (col_a <op> col_b)` per row over non-null pairs and returns the fraction of violations. Supports `>`, `>=`, `<`, `<=`, `=`, `!=`. A score of 0.0 means every non-null pair satisfies the rule. Used for ordering invariants and budget constraints.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `col_a` | `str` | `"a"` | Left-hand column name |
| `col_b` | `str` | `"b"` | Right-hand column name |
| `operator` | `str` | `">"` | One of `>`, `>=`, `<`, `<=`, `=`, `!=` |

## Assumptions

- Both columns are non-null where the rule must hold; nulls in either column are excluded by the SQL.
- Types of `col_a` and `col_b` are compatible for the chosen operator under the warehouse's implicit casting rules.
- Operator semantics match the business invariant exactly (e.g. `<=` vs `<`).

## When it works well

- Timestamp ordering invariants (`shipped_at >= created_at`).
- Budget / actual constraints (`actual_cost <= budget`).
- Denormalised-copy equality assertions across two columns.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Nulls excluded from denominator | Null rows in either column are silently skipped and inflate the apparent pass rate | Pair with `null_fraction` on each column; treat null in a mandatory pair as a violation |
| Timezone-offset comparisons | Rule passes when both timestamps are in UTC but fires when one is in local time | Normalise to UTC at ingest or wrap in `AT TIME ZONE 'UTC'` |
| Type mismatch between col_a and col_b | Implicit casting either succeeds silently or fails with a warehouse error | Cast explicitly; use `sql_assertion_violation` for richer expressions |
| Clock skew on near-simultaneous events | `shipped_at >= created_at` fires on millisecond-scale skew | Add a grace via `sql_assertion_violation` with `>= created_at - INTERVAL '1 second'` |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | 0% | Deterministic rule; bounds determine FPR exactly |
| Lognormal | 0% | Deterministic rule |
| Poisson | 0% | Deterministic rule |
| Beta | 0% | Deterministic rule |
| Pareto | 0% | Deterministic rule |
| Exponential | 0% | Deterministic rule |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | 0% |
| Lognormal | (default) | 0% |
| Poisson | (default) | 0% |
| Beta | (default) | 0% |
| Pareto | (default) | 0% |
| Exponential | (default) | 0% |

## Citation

No statistical reference; rule-based check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="orders",
    detector_slug="column_pair_comparison",
    params={'col_a': 'shipped_at', 'col_b': 'created_at', 'operator': '>='},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Deterministic — FPR is 0% when the rule is correct.
- All practical false positives come from incorrect operator choice or timezone confusion.
- Nulls are silently excluded; check `null_fraction` separately if nulls are forbidden.

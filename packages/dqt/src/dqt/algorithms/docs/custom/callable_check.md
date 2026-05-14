# Callable check (`callable_check`)

**Group:** `custom` · **Kind:** `sample` · **Version:** `1` · **Min N:** 1

## What it computes

Wraps any Python function `fn(df) -> float` as a first-class dqt detector. At fit time the function is called on the reference DataFrame; at score time on the current DataFrame, the return value is clipped to `[0, 1]` and passed to the standard verdict routing.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `fn` | `Callable[[pd.DataFrame], float]` | `(required)` | Function accepting a pandas DataFrame and returning a float in [0, 1] |

## Assumptions

- The callable is pure and deterministic on a given DataFrame (no random state, no external reads).
- The return value is in `[0, 1]` where higher is worse; values outside are silently clipped.
- The callable is in-process — it does not re-read the warehouse.

## When it works well

- Domain-specific business rules that combine multiple columns.
- Wrapping an existing internal scoring function as a dqt check.
- Rapid prototyping before a custom detector is formalised in `dqt.algorithms.*`.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Non-deterministic callable | Different runs produce different verdicts on identical data | Make the callable pure; no random seeds, no external state reads at score time |
| Score outside [0, 1] | Score is silently clipped; logic returning 500 looks like 1.0 | Normalise the return value inside the callable |
| Exception inside callable | DetectorError instead of a verdict | Wrap risky logic in try/except inside the callable and return 1.0 fail-safe |
| Callable reads from the warehouse | Violates the read-once sampling contract | Receive an already-sampled DataFrame; move queries to the adapter |
| Not serialisable to YAML | Check cannot be persisted to a YAML file | Use `sql_assertion_violation` or `remote_check` for portable checks |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | user-defined | Determined entirely by the supplied function |
| Lognormal | user-defined | Determined entirely by the supplied function |
| Poisson | user-defined | Determined entirely by the supplied function |
| Beta | user-defined | Determined entirely by the supplied function |
| Pareto | user-defined | Determined entirely by the supplied function |
| Exponential | user-defined | Determined entirely by the supplied function |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | user-defined |
| Lognormal | (default) | user-defined |
| Poisson | (default) | user-defined |
| Beta | (default) | user-defined |
| Pareto | (default) | user-defined |
| Exponential | (default) | user-defined |

## Citation

Extension point; no external algorithmic reference.

Implementation: `packages/dqt/src/dqt/algorithms/custom/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    detector_slug="callable_check",
    params={'fn': "lambda df: float((df['amount'] > 1000).mean())"},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Cannot be serialised to YAML — Python-only.
- Failures and FPR are entirely user-controlled by the function body.
- Cannot run in sandboxed or remote environments without the callable being importable.

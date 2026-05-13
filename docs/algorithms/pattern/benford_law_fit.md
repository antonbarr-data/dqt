# Benford's Law fit (`benford_law_fit`)

**Group:** `pattern` · **Kind:** `sample` · **Version:** `1` · **Min N:** 30

## What it computes

Extracts the first significant digit (1–9) from non-zero absolute values, computes observed digit frequencies, and runs `scipy.stats.chisquare` against the Benford expected counts. Score = `1 - p_value`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- Values are naturally occurring and span multiple orders of magnitude.
- At least 30 non-zero values; chi-square approximation requires a moderate N.
- Values are individual records (not pre-aggregated buckets).

## When it works well

- Financial auditing, fraud detection, invoice/transaction monitoring.
- Detecting systematic rounding or capping artefacts.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Narrow-range columns (0–100, 1–5) | Benford's Law does not apply | Verify column spans ≥ 2 orders of magnitude before enabling |
| Sequential IDs or assigned numbers | Benford's Law does not apply | Use `uniqueness` / `regex_match` for assigned numbers |
| Small N | Chi-square test of Benford fit needs > 200 rows for power | Aggregate by time window to accumulate rows |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | N/A | Benford's Law does not apply to bounded normal data |
| Lognormal | ~5% | Spans multiple orders of magnitude; calibrated |
| Poisson | N/A | Bounded; Benford does not apply |
| Beta | N/A | Bounded; Benford does not apply |
| Pareto | ~5-8% | Power-law; close to Benford |
| Exponential | ~5-7% | Right-skew with multi-order spread |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | N/A |
| Lognormal | (default) | ~5% |
| Poisson | (default) | N/A |
| Beta | (default) | N/A |
| Pareto | (default) | ~5-8% |
| Exponential | (default) | ~5-7% |

## Citation

Benford, F. (1938). The law of anomalous numbers. *Proceedings of the American Philosophical Society*, 78(4), 551–572.

Implementation: `packages/dqt/src/dqt/algorithms/pattern/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    column_name="amount_paid_usd",
    detector_slug="benford_law_fit",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Only meaningful on naturally-occurring, multi-scale numeric columns.
- Reports a hypothesis test, not a magnitude.

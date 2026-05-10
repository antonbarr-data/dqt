# Quickstart

Five minutes to your first data quality check using the Gigler sample dataset.

## Install

```bash
pip install dqtlib
```

## End-to-end example

The Gigler dataset ships in `examples/gigler/data/`. This walkthrough runs checks against the transactions CSV.

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.local import LocalAdapter

# Load the sample data
df = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q1.csv")

# LocalAdapter wraps any in-memory DataFrame
adapter = LocalAdapter({"public.gigler_transactions": df})

store = MemoryStore()
runner = Runner(store)

# --- 1. Completeness check on a critical column ---
check = Check(
    schema_name="public",
    table_name="gigler_transactions",
    column_name="amount_usd",
    detector_slug="null_fraction",
)
result = runner.run(check, adapter)
print(result.verdict)        # Verdict.pass_
print(result.plain_english)  # "0.00% of values are null — within the 1% warn threshold"

# --- 2. Outlier detection on transaction amounts ---
check = Check(
    schema_name="public",
    table_name="gigler_transactions",
    column_name="amount_usd",
    detector_slug="mad_outlier_fraction",
    params={"threshold": 3.5},
)
result = runner.run(check, adapter)
print(result.plain_english)

# --- 3. Value set check on transaction status ---
check = Check(
    schema_name="public",
    table_name="gigler_transactions",
    column_name="status",
    detector_slug="set_membership",
    params={"allowed_values": ["completed", "cancelled", "pending", "refunded"]},
)
result = runner.run(check, adapter)
print(result.verdict)

# --- 4. Drift detection: compare Q1 vs Q2 ---
df_q1 = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q1.csv")
df_q2 = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q2.csv")

adapter_q2 = LocalAdapter({"public.gigler_transactions": df_q2})

check = Check(
    schema_name="public",
    table_name="gigler_transactions",
    column_name="amount_usd",
    detector_slug="ks_pvalue",
)
# Fit baseline on Q1, score on Q2
runner.fit(check, LocalAdapter({"public.gigler_transactions": df_q1}))
result = runner.run(check, adapter_q2)
print(result.plain_english)  # Reports whether amount distribution shifted
```

## Reading a result

Every `runner.run()` returns a `RunResult`:

```python
result.verdict        # Verdict.pass_ | Verdict.warn | Verdict.fail
result.score          # float — the raw numeric score (0.0 = best for most detectors)
result.plain_english  # "0.82% of values are outliers — within the 1% warn threshold"
result.details        # dict with detector-specific breakdown
result.diagnostic_sql # SQL WHERE clause to inspect the failing rows
result.check_id       # UUID of the check that produced this result
result.detector_slug  # "mad_outlier_fraction"
```

## Incident tracking

When a check returns `warn` or `fail`, dqt automatically creates an `Incident` in the store:

```python
incidents = store.list_incidents(check.id)
for inc in incidents:
    print(inc.severity, inc.score, inc.opened_at)
```

## Next steps

- [All detectors reference](detectors.md) — complete list with parameters and Gigler examples
- [Check model and Runner API](checks-and-runner.md) — scopes, filters, baselines
- [YAML check format](yaml-reference.md) — run checks from config files
- [CLI reference](cli-reference.md) — `dqt run`, `dqt version`
- [Connecting to warehouses](adapters.md) — LocalAdapter, PostgresAdapter

# Results, Incidents & AI Explanations

## RunResult

Every call to `runner.run()` returns a `RunResult`. It carries the full verdict, score, human-readable summary, and detector-specific breakdown.

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.local import LocalAdapter

df = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q2.csv")
adapter = LocalAdapter({"public.gigler_transactions": df})
runner = Runner(MemoryStore())

result = runner.run(Check(
    schema_name="public",
    table_name="gigler_transactions",
    column_name="amount_usd",
    detector_slug="mad_outlier_fraction",
    params={"threshold": 3.5},
), adapter)
```

### All fields

| Field | Type | Description |
|-------|------|-------------|
| `verdict` | `Verdict` | `Verdict.pass_`, `Verdict.warn`, or `Verdict.fail` |
| `score` | `float` | Raw detector output (fraction, p-value, z-score, etc.) |
| `plain_english` | `str` | Human-readable verdict — e.g. `"0.82% of values are outliers — within the 1% warn threshold"` |
| `details` | `dict` | Detector-specific breakdown (see per-detector docs) |
| `diagnostic_sql` | `str \| None` | WHERE clause to pull the failing rows from the warehouse |
| `check_id` | `UUID` | ID of the check that produced this result |
| `detector_slug` | `str` | Slug of the detector that ran |
| `run_id` | `UUID` | Unique ID for this run |
| `started_at` | `datetime` | When the run started |
| `finished_at` | `datetime` | When the run finished |

```python
print(result.verdict)         # Verdict.pass_
print(result.score)           # 0.0082
print(result.plain_english)   # "0.82% of values are outliers — within the 1% warn threshold"
print(result.diagnostic_sql)  # "amount_usd > 487.3 OR amount_usd < -12.4"

# Detector-specific breakdown
print(result.details)
# {
#   "outlier_count": 82,
#   "total_count": 10000,
#   "mad": 45.2,
#   "median": 127.8,
#   "lower_fence": -12.4,
#   "upper_fence": 487.3,
# }
```

---

## Verdict enum

```python
from dqt.checks.models import Verdict

Verdict.pass_   # check passed
Verdict.warn    # score exceeded warn threshold
Verdict.fail    # score exceeded fail threshold
```

Compare in code:

```python
if result.verdict == Verdict.fail:
    print(f"FAIL: {result.plain_english}")
    print(f"Inspect failing rows with: WHERE {result.diagnostic_sql}")
```

---

## Accessing causal discovery results

After running `causal_runner.discover()`, the result is a `CausalDAG` — a directed graph of metric→metric influence.

```python
from dqt.causality import CausalRunner, CausalConfig

causal_runner = CausalRunner(config=CausalConfig(method="pcmci_plus", max_lag=4))

# metric_panel is a dict of {metric_id: pd.Series with DatetimeIndex}
dag = causal_runner.discover(metric_panel)

# Iterate discovered edges
for edge in dag.edges:
    print(f"{edge.source} → {edge.target}")
    print(f"  lag: {edge.lag_weeks} weeks")
    print(f"  confidence: {edge.confidence:.2f}")
    print(f"  e_value: {edge.e_value:.2f}")   # E-value < 1.5 = fragile
    print(f"  method_stats: {edge.method_stats}")  # Granger F, Transfer Entropy, etc.

# Get all parents of a metric
parents = dag.parents("weekly_transaction_volume")

# Shapley attribution for a given time point
attribution = dag.shapley_attribution(
    target="weekly_transaction_volume",
    t="2024-04-15",
    metric_panel=metric_panel,
)
for driver, share in attribution.items():
    print(f"  {driver}: {share:+.1%} contribution")
```

### CausalEdge fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | `str` | Upstream metric ID |
| `target` | `str` | Downstream metric ID |
| `kind` | `str` | `"causality"`, `"aggregates"`, `"filters"` |
| `lag_weeks` | `int \| None` | Detected lag in weeks |
| `confidence` | `float` | Stability-selection confidence (0–1) |
| `e_value` | `float \| None` | Sensitivity to unobserved confounders — values < 1.5 shown as "fragile" in UI |
| `description` | `str \| None` | Human-authored or agent-generated description |
| `method_stats` | `dict` | Raw statistics: Granger F-statistic, Transfer Entropy bits, etc. |

---

## Accessing AI (agent) explanations

The agent explanation is triggered by `runner.explain(incident, adapter)` or accessed on an incident object after the agent loop runs in the server.

```python
from dqt.agent import AgentExplainer

explainer = AgentExplainer()

explanation = explainer.explain(
    incident=incident,
    adapter=adapter,
    dag=dag,           # optional — causal DAG for the metric panel
)

print(explanation.plain_english)
# "The null_fraction on amount_usd spiked to 12% at 03:00 UTC.
#  The most likely driver is stg_payments (lineage parent, 2-hop upstream)
#  which introduced a schema break at 01:40 UTC — the payment_method column
#  was dropped, causing amount_usd to go NULL for all card transactions."

print(explanation.confidence)        # 0.87
print(explanation.level)             # "intervention" (Pearl ladder: association/intervention/counterfactual)

for ev in explanation.evidence:
    print(ev.kind)       # "lineage" | "detector" | "dag_edge" | "incident_history"
    print(ev.label)      # "stg_payments schema break"
    print(ev.detail)     # "payment_method column removed at 2024-04-15T01:40:00Z"
    print(ev.source_ref) # reference back to the lineage node or DAG edge

for q in explanation.follow_up_questions:
    print(q)
# "Did any dbt model change deploy between 01:00 and 02:00?"
# "Is amount_usd nullable for non-card payment methods normally?"
```

### Explanation fields

| Field | Type | Description |
|-------|------|-------------|
| `plain_english` | `str` | Full narrative explanation |
| `confidence` | `float` | Agent's self-reported confidence (0–1) |
| `level` | `str` | Pearl ladder level: `"association"`, `"intervention"`, `"counterfactual"` |
| `evidence` | `list[Evidence]` | Cited evidence items with source references |
| `follow_up_questions` | `list[str]` | Suggested next investigative steps |
| `incident_id` | `UUID` | Incident this explanation covers |
| `model` | `str` | Claude model ID used |
| `token_usage` | `dict` | `{"input": int, "output": int}` |

---

## Querying the MemoryStore

```python
from dqt import Runner, MemoryStore
from dqt.checks.models import Verdict

store = MemoryStore()
runner = Runner(store)

# ... run checks ...

# All runs for a check
runs = store.list_runs(check.id, limit=50)

# Filter to failures only
failures = [r for r in runs if r.verdict == Verdict.fail]

# All open incidents across all checks
incidents = store.list_incidents()
open_incidents = store.list_incidents(status="open")

# Incidents for a specific check
check_incidents = store.list_incidents(check_id=check.id)

# Get the run that opened an incident
triggering_run = store.get_run(incident.run_id)
```

### Incident fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Incident identifier |
| `check_id` | `UUID` | Check that fired |
| `run_id` | `UUID` | Run that opened the incident |
| `severity` | `Verdict` | `Verdict.warn` or `Verdict.fail` |
| `score` | `float` | Score at time of opening |
| `plain_english` | `str` | Verdict string from the triggering run |
| `opened_at` | `datetime` | When the incident was created |
| `resolved_at` | `datetime \| None` | When it was resolved (None if still open) |
| `status` | `str` | `"open"` or `"resolved"` |

---

## Routing on results in CI

```python
import sys
from dqt import Check, Runner, MemoryStore
from dqt.adapters.local import LocalAdapter
from dqt.checks.models import Verdict

store = MemoryStore()
runner = Runner(store)
adapter = LocalAdapter({"public.gigler_transactions": df})

checks = [...]  # your check list

results = [runner.run(c, adapter) for c in checks]

for r in results:
    icon = {"pass_": "✓", "warn": "⚠", "fail": "✗"}[r.verdict.value]
    print(f"{icon}  {r.detector_slug:<35} {r.plain_english}")

if any(r.verdict == Verdict.fail for r in results):
    sys.exit(1)   # non-zero exit code fails the CI job
```

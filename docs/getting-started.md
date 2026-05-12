# Getting started with dqt

dqt is a Python library that watches your data for statistical drift, outliers, schema changes, and — uniquely — surfaces *why* metrics moved by running causal discovery across your time series. This guide takes you from zero to your first working check in about five minutes, then walks through the dashboard, profiling, and causality features.

---

## Prerequisites

- Python 3.12 or later
- `pip` (comes with Python)

No database, no server, no Docker required for the examples in this guide.

---

## 1. Install

```bash
pip install dqtlib
```

To also get the local browser dashboard:

```bash
pip install "dqtlib[dashboard]"
```

Verify the install:

```bash
dqt version
# dqtlib 0.4.4
```

---

## 2. Your first check — null fraction

The simplest check asks: *how many nulls does this column have?* Open a Python file or notebook and paste this:

```python
import pandas as pd
from dqt import Runner, MemoryStore
from dqt.checks.models import Check, CheckScope
from dqt.adapters.local import LocalAdapter

# Sample data — replace with your own DataFrame or CSV
df = pd.DataFrame({
    "email": ["a@x.com", None, "c@x.com", "d@x.com", None, "f@x.com"],
    "amount": [10.0, 20.0, 15.0, 30.0, 25.0, 18.0],
})

store = MemoryStore()
runner = Runner(store)
adapter = LocalAdapter(df, table_name="customers")

check = Check(
    schema_name="public",
    table_name="customers",
    column_name="email",
    detector_slug="null_fraction",
)

result = runner.run(check, adapter)

print(result.verdict)       # pass | warn | fail
print(result.score)         # 0.3333  (2 of 6 are null)
print(result.plain_english) # "33.33% of emails are null — above the 1% warn threshold"
```

**Understanding the result:**

| Field | What it means |
|---|---|
| `verdict` | `pass` — within threshold · `warn` — above warn threshold · `fail` — above fail threshold |
| `score` | The raw metric value (null fraction = 0.33 means 33% of rows are null) |
| `plain_english` | A human-readable sentence explaining exactly what happened |
| `details` | A dict of supporting numbers (`n_null`, `n_total`, thresholds) |

In this case `score = 0.33` is well above the default 1% warn threshold, so the verdict is `fail`.

---

## 3. Drift detection — Wasserstein distance

A null fraction check is a rule. A drift check is statistical: it asks whether the *shape* of a column has changed since a reference window.

```python
import numpy as np
import pandas as pd
from dqt import Runner, MemoryStore
from dqt.checks.models import Check, CheckScope
from dqt.adapters.local import LocalAdapter

rng = np.random.default_rng(42)

# Reference window: last month's order amounts (roughly log-normal)
reference = pd.DataFrame({"amount": rng.lognormal(5.0, 0.5, 1000)})
# Current window: amounts have shifted upward by ~30%
current   = pd.DataFrame({"amount": rng.lognormal(5.4, 0.5, 1000)})

store = MemoryStore()
runner = Runner(store)

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="wasserstein_1",  # earth-mover distance between distributions
)

result = runner.run_in_memory(check, reference=reference, current=current)

print(result.verdict)       # warn or fail depending on the distance
print(result.plain_english)
# → "Wasserstein distance 0.28 — above the 0.20 warn threshold. Distribution has
#    shifted rightward; tail values are heavier than the reference window."
```

`run_in_memory` skips the adapter — pass `reference` and `current` DataFrames directly. Useful for notebooks.

**Other drift detectors worth knowing:**
- `ks_pvalue` — Kolmogorov–Smirnov two-sample test (great for shape changes)
- `psi` — Population Stability Index (standard in financial modelling)
- `adwin` — adaptive windowing for streaming data

---

## 4. Outlier detection

```python
check = Check(
    schema_name="public",
    table_name="sessions",
    column_name="duration_s",
    detector_slug="mad_outlier_fraction",  # modified Z-score (MAD-based)
)
```

`mad_outlier_fraction` uses the median absolute deviation rather than standard deviation — it is robust to the heavy-tailed distributions common in session durations, revenue, and latency columns. The score is the fraction of rows flagged as outliers.

For high-dimensional tables (many columns), try `isolation_forest_fraction` or `ecod` — they detect multivariate anomalies where no single column is unusual in isolation.

---

## 5. Run checks from the CLI

Save your checks as a YAML manifest and run them without writing Python:

```yaml
# checks.yaml
version: "1"

source:
  type: csv
  id: orders
  path: data/orders.csv
  table_name: orders

checks:
  - schema_name: public
    table_name: orders
    column_name: amount_usd
    detector_slug: null_fraction

  - schema_name: public
    table_name: orders
    column_name: amount_usd
    detector_slug: mad_outlier_fraction

  - schema_name: public
    table_name: orders
    column_name: status
    detector_slug: set_membership
    params:
      allowed_values: [completed, cancelled, pending, refunded]
```

Then:

```bash
dqt run checks.yaml
```

Output:

```
✓  public.orders  null_fraction      amount_usd  0.00%  — within threshold
✓  public.orders  mad_outlier_fraction  amount_usd  0.82%  — within threshold
⚠  public.orders  set_membership     status      3.10%  — above 1% warn threshold
```

Exit code `0` if all checks pass, `1` if any returns `fail`. Wire it into CI the same way you would `pytest`.

---

## 6. Open the local dashboard

The dashboard shows all check results in a browser — no server required.

```python
import threading
import uvicorn
from dqt.dashboard import create_app

# store is the same MemoryStore you ran checks into
app = create_app(store=store)

thread = threading.Thread(
    target=uvicorn.run,
    kwargs={"app": app, "host": "127.0.0.1", "port": 8080},
    daemon=True,
)
thread.start()
print("→ http://127.0.0.1:8080")
```

Or from the terminal (starts with an empty store):

```bash
dqt dashboard --port 8080
```

The dashboard has three views:

| View | URL | What it shows |
|---|---|---|
| **Checks** | `/` | Latest score, verdict, and plain-English summary per check. Click a row for run history. |
| **Profile** | `/profile/<dataset>` | Column distribution shapes (normal / skewed / heavy-tailed / multimodal), skewness, kurtosis, medcouple. |
| **Causality** | `/causality` | Granger pairwise causality edges — evidence strength, lag, F-statistic, BH-FDR corrected p-values, confounder candidates. |

---

## 7. Profile a dataset

Column profiling characterises the shape of every numeric column — useful before choosing which detector to apply.

```python
from dqt.algorithms.distribution.profiler import profile_dataframe
from dqt.store._protocol import ProfileReport
from datetime import datetime

report_dict = profile_dataframe(df)

# Save into the store so the dashboard can show it
store.save_profile_report(ProfileReport(
    dataset_name="orders",
    ran_at=datetime.now(),
    n_rows=report_dict["n_rows"],
    n_numeric_columns=report_dict["n_numeric_columns"],
    columns=report_dict["columns"],
))
```

`profile_dataframe` uses D'Agostino–Pearson normality tests, Sarle's bimodality coefficient, and the medcouple robust skewness measure to classify each column's distribution shape. The dashboard's `/profile/orders` page renders the full breakdown.

**Practical use:** if a column is classified `heavy_tailed`, default to `mad_outlier_fraction` over `zscore_outlier_fraction` (Z-score assumes Gaussianity and produces false positives on heavy tails).

---

## 8. Granger causality inference

Once you have a panel of metric time series (e.g. daily revenue, session count, ad spend, churn rate), dqt can run Granger pairwise causality to discover which metrics predict others with a lag.

```python
import pandas as pd
import numpy as np
from dqt.causality.granger import granger_pairwise
from dqt.store._protocol import CausalityReport
from datetime import datetime

rng = np.random.default_rng(0)
n = 120  # 120 days of data

ad_spend    = rng.normal(1000, 100, n)
gig_views   = 0.4 * np.roll(ad_spend, 1) + rng.normal(5000, 200, n)
bookings    = 0.3 * np.roll(gig_views, 2) + rng.normal(300, 30, n)
daily_rev   = 150 * bookings + rng.normal(0, 5000, n)

panel = pd.DataFrame({
    "ad_spend": ad_spend,
    "gig_views": gig_views,
    "bookings": bookings,
    "daily_revenue": daily_rev,
})

report = granger_pairwise(panel, max_lag=4)

for edge in report.significant_edges:
    print(f"{edge.cause} → {edge.effect}  "
          f"lag={edge.selected_lag}  "
          f"F={edge.f_statistic:.1f}  "
          f"evidence={edge.evidence_strength}")
# gig_views → bookings   lag=2  F=47.3  evidence=strong
# ad_spend  → gig_views  lag=1  F=21.8  evidence=strong
# ad_spend  → bookings   lag=2  F=7.6   evidence=moderate
```

Key things to know:
- The function runs BH-FDR correction across all tested pairs — this is not a simple p < 0.05 cut (which would have ~5% false positive rate when testing 20 pairs).
- `differenced=True` on an edge means the series was auto-differenced to achieve stationarity before testing.
- `confounder_candidates` lists metrics Z such that both Z→X and Z→Y are significant — a reason to be cautious about interpreting the X→Y edge causally.
- Edges are hypotheses, not facts. In production, every edge goes through a human review queue before entering the confirmed DAG.

Save to the store for the dashboard:

```python
store.save_causality_report(CausalityReport(
    dataset_name="metrics_panel",
    ran_at=datetime.now(),
    n_pairs_tested=len(report.edges),
    n_significant=len(report.significant_edges),
    edges=[e.__dict__ if hasattr(e, "__dict__") else e for e in report.to_dict()["edges"]],
))
```

---

## 9. What's next

| Topic | Where to look |
|---|---|
| Connect to a real warehouse | [docs/api/adapters.md](api/adapters.md) — Postgres, BigQuery, Snowflake, ClickHouse, DuckDB |
| Full YAML reference | [docs/api/yaml-reference.md](api/yaml-reference.md) |
| All detectors with parameters | [docs/api/detectors.md](api/detectors.md) |
| Dashboard deep-dive | [docs/dashboard.md](dashboard.md) |
| Semantic layer (metric definitions) | [docs/semantic-layer.md](semantic-layer.md) |
| dbt manifest ingestion | [docs/api/adapters.md](api/adapters.md#dbt) |
| Run in CI (GitHub Actions example) | [docs/api/cli-reference.md](api/cli-reference.md#using-in-ci) |
| Algorithm references | [docs/algorithms/](algorithms/) — one page per detector slug |

---

## Quick reference: common detector slugs

| What you want to check | Slug | Notes |
|---|---|---|
| Are there nulls? | `null_fraction` | Rule-based. Threshold: warn 1%, fail 5% |
| Has the distribution shifted? | `wasserstein_1` | Earth-mover distance. Good default for continuous columns |
| Are there outliers? (robust) | `mad_outlier_fraction` | MAD-based. Use for heavy-tailed data |
| Are there outliers? (many columns) | `isolation_forest_fraction` | Multivariate. Detects anomalies invisible in single columns |
| Has the schema changed? | `schema_change` | Detects added/removed columns and type changes |
| Is data arriving on time? | `freshness_seconds_behind` | Checks `max(timestamp_col)` against expected lag |
| Is row volume stable? | `volume` | % change from reference window |
| Are values in an allowed set? | `set_membership` | Pass a list of `allowed_values` |
| Is the distribution stable? (p-value) | `ks_pvalue` | KS two-sample test. Score is the test statistic |
| Time-series level shift | `bocpd` | Bayesian online changepoint detection |

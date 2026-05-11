# Python library quickstart

## Installation

```bash
pip install dqt
```

Optional extras:

```bash
pip install "dqt[forecast]"   # Prophet-based time-series detectors
pip install "dqt[causal]"     # PCMCI+, tigramite
pip install "dqt[deep]"       # autoencoder-based detectors
```

## Basic check — null fraction

Every check binds a detector slug to a table (and optionally a column), then runs `fit` on a reference sample followed by `score` on the current window.

```python
import pandas as pd
import dqt
from dqt import Check, Runner, MemoryStore
from dqt_cli.adapter_factory import CliDuckDBAdapter
from dqt_cli.manifest import SourceConfig

# Build a minimal in-memory adapter from a CSV file
source = SourceConfig(type="csv", path="orders.csv", table_name="orders")
adapter = CliDuckDBAdapter(source)

# Define a check: warn when >1 % of `customer_id` values are NULL, fail at >5 %
check = Check(
    schema_name="main",
    table_name="orders",
    column_name="customer_id",
    detector_slug="null_fraction",
)

store = MemoryStore()
runner = Runner(store)

# fit() computes the reference state from the current data
runner.fit(check, adapter)

# run() scores the current window and writes to the store
result = runner.run(check, adapter)

print(result.verdict)        # Verdict.pass_ | Verdict.warn | Verdict.fail
print(result.score)          # e.g. 0.0023  (2.3 % null)
print(result.plain_english)  # "23/10000 rows are NULL (0.2%)"
```

## Completeness check

`completeness` measures the fraction of non-null values (1 − null_fraction). The verdict thresholds are warn < 95 %, fail < 90 %.

```python
check = Check(
    schema_name="main",
    table_name="orders",
    column_name="amount",
    detector_slug="completeness",
)
runner.fit(check, adapter)
result = runner.run(check, adapter)
print(result.plain_english)
# "Completeness is 99.8% (baseline 99.8%)"
```

## Drift detection with Wasserstein-1

`wasserstein_1` measures the earth-mover distance between distributions, normalised by the reference standard deviation. It is the right tool when you care about **how much** the distribution shifted (magnitude), not just whether it did. KS (`ks_pvalue`) is complementary — it answers "did anything change at all?" but gives no sense of scale; Wasserstein-1 gives you the shift in interpretable units (σ).

```python
import numpy as np

# Simulate reference and current DataFrames — 30% mean shift on a revenue column
ref_df  = pd.DataFrame({"amount": np.random.normal(100, 10, 10_000)})
curr_df = pd.DataFrame({"amount": np.random.normal(130, 10, 10_000)})  # +30% mean shift

from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

detector = Wasserstein1Detector()
state   = detector.fit(ref_df)
result  = detector.score(curr_df, state)

print(result.verdict)        # Verdict.fail  (shift >> warn threshold of 0.2σ)
print(result.plain_english)  # "Wasserstein-1 distance = 3.00σ — large shift"
print(result.details)        # {"wasserstein_distance": 30.0, "ref_std": 10.0, "normalized": 3.0}
```

Use `ks_pvalue` when you need a significance test (p-value) or when the shift is in the tails rather than the mean. Use `wasserstein_1` when you need an interpretable magnitude on continuous numeric columns.

## Outlier detection (MAD)

`mad_outlier_fraction` uses the modified Z-score (Leys et al. 2013). It is robust to heavy tails and skewed distributions; prefer it over `zscore_outlier_fraction` for non-normal columns.

```python
from dqt.algorithms.outliers_uni.mad import MADOutlierDetector

detector = MADOutlierDetector(threshold=3.5)  # default threshold

ref_df  = pd.DataFrame({"value": np.random.exponential(scale=10, size=5_000)})
curr_df = pd.DataFrame({"value": np.append(
    np.random.exponential(scale=10, size=4_990),
    [9999.0] * 10,  # injected outliers
)})

state  = detector.fit(ref_df)
result = detector.score(curr_df, state)
print(result.plain_english)
# "0.2% of values are outliers (modified Z > 3.5)"
```

For skewed distributions use `DoubleMadOutlierDetector`, which computes separate left and right MAD:

```python
from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector
detector = DoubleMadOutlierDetector(threshold=3.5)
```

## Multivariate outliers (Isolation Forest)

`isolation_forest_fraction` works on all numeric columns simultaneously.

```python
from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector

ref_df = pd.DataFrame({
    "amount":   np.random.normal(100, 10, 5_000),
    "quantity": np.random.poisson(5, 5_000).astype(float),
})
curr_df = ref_df.copy()
curr_df.iloc[-5:] = [9999.0, 9999.0]  # inject multivariate anomalies

detector = IsolationForestDetector(contamination=0.05)
state    = detector.fit(ref_df)
result   = detector.score(curr_df, state)
print(result.plain_english)
# "0.1% of rows flagged as multivariate outliers by Isolation Forest"
```

## Time-series anomaly detection (STL)

`stl_residual_zscore` decomposes the series with STL (Cleveland et al. 1990) and scores the maximum absolute Z-score of the residuals. Requires at least `2 * period + 1` observations.

```python
from dqt.algorithms.timeseries.stl import STLAnomalyDetector

# Daily data, weekly seasonality
dates  = pd.date_range("2024-01-01", periods=90, freq="D")
values = np.sin(np.arange(90) * 2 * np.pi / 7) * 10 + 100 + np.random.normal(0, 1, 90)
df     = pd.DataFrame({"metric": values}, index=dates)

detector = STLAnomalyDetector(period=7)
state    = detector.fit(df)

# Current window with a spike injected
curr = df.copy()
curr.iloc[-1] = 200.0
result = detector.score(curr, state)
print(result.plain_english)
# "Max STL residual Z-score 12.34 (1 anomalous point)"
```

## Volume check

```python
check = Check(
    schema_name="main",
    table_name="orders",
    detector_slug="volume",
    # column_name not required — volume is a table-level check
)
runner.fit(check, adapter)
result = runner.run(check, adapter)
# "Row count 10,234 is 2.3% above baseline (10,000)"
```

## Reading results from the store

```python
# List the last 10 runs for a check
runs = store.list_runs(check.id, limit=10)
for r in runs:
    print(r.started_at, r.verdict, r.score)

# List open incidents
incidents = store.list_incidents(check.id, status="open")
for inc in incidents:
    print(inc.opened_at, inc.severity, inc.score)
```

## Distribution profiling

`classify_distribution` characterises a numeric array and returns a `DistributionProfile`. Use it to choose the right detector automatically.

```python
import numpy as np
from dqt.algorithms.distribution.profiler import classify_distribution, DistributionType

values = np.random.lognormal(mean=0, sigma=1, size=10_000)
profile = classify_distribution(values)

print(profile.distribution_type)   # DistributionType.SKEWED_POSITIVE
print(profile.skewness)            # e.g. 6.18
print(profile.is_normal)           # False
print(profile.medcouple)           # e.g. 0.39

# Choose detector based on shape
if profile.distribution_type in (
    DistributionType.SKEWED_POSITIVE,
    DistributionType.SKEWED_NEGATIVE,
):
    # asymmetric tails — use double-MAD, not plain Z-score
    from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector
    detector = DoubleMadOutlierDetector()
elif profile.is_normal:
    from dqt.algorithms.outliers_uni.zscore import ZScoreOutlierDetector
    detector = ZScoreOutlierDetector()
```

## Verdict levels

| `Verdict` | Meaning |
|---|---|
| `Verdict.pass_` | Score within normal bounds |
| `Verdict.warn` | Score exceeds the warn threshold |
| `Verdict.fail` | Score exceeds the fail threshold |

Thresholds are defined per slug in `dqt.algorithms._scales.STAT_SCALES`. The `FreshnessDetector` uses instance-level thresholds (`warn_seconds`, `fail_seconds`) instead, because freshness SLAs vary per table.

## Using `Runner` with scopes and filters

`CheckScope` limits the rows fetched for a check. `CheckFilter` applies equality filters before sampling.

```python
from dqt import Check, CheckScope, CheckFilter

check = Check(
    schema_name="main",
    table_name="events",
    column_name="user_id",
    detector_slug="null_fraction",
    # Only check rows since the last pipeline run
    scope=CheckScope(mode="incremental", key_col="created_at", since="2024-06-01T00:00:00"),
    # Only check a specific region
    filters=[CheckFilter(col="region", values=["EU"])],
    # Sample 10 % of matching rows instead of a fixed row count
    sampling_pct=10.0,
)
```

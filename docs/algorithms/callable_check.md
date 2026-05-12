# `custom.callable_check`

> *Custom callable score* — wraps any Python function that accepts a DataFrame and returns a float as a first-class dqt detector, with the same verdict and STAT_SCALES integration as built-in detectors.

## What it does

At fit time, calls `fn(reference_df)` and stores the result as `ref_score` in state. At score time, calls `fn(current_df)`, clips the result to `[0, 1]`, and runs it through `_verdict()` using the standard warn/fail thresholds. The function receives the full DataFrame — all columns — so it can implement arbitrary multi-column logic. The only contract is that it returns a single float. No fitting is performed on the reference in the statistical sense; the reference call is informational (the `ref_score` is stored in `details` for comparison but does not influence the verdict directly).

This is the primary extension point for domain logic that cannot be expressed as a combination of existing detectors. It integrates fully with dqt's runner, HITL queue, incident lifecycle, and audit log.

## When to use it

- Business-rule checks that involve multiple columns or conditional logic — e.g. "what fraction of `fct_gigs` rows have a suspicious price-to-delivery ratio?"
- One-off data quality assertions during dbt CI runs where you want the dqt verdict format without writing a full detector class.
- Wrapping an existing internal scoring function that already produces a [0, 1] metric.
- Rapid prototyping before a custom detector is formalised into `packages/dqt/src/dqt/algorithms/`.

## When not to use it

- When statistical correctness matters and you are reimplementing an existing method — prefer the canonical detector (e.g. `mad_outlier_fraction`) to avoid diverging implementations.
- Functions that return values outside [0, 1] without normalisation — the score is silently clipped; make your function return a properly bounded value or use a built-in detector with an appropriate scale.
- When the check must run in a sandboxed or serialised context (e.g. stored in a YAML check file) — `callable_check` is Python-only and cannot be serialised to YAML; use `sql_assertion_violation` or `remote_check` for portable checks.
- Expensive functions that scan large DataFrames — dqt already samples the warehouse; do not re-read from the database inside `fn`.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `fn` | `Callable[[pd.DataFrame], float]` | *(required)* | Any callable that accepts a pandas DataFrame and returns a float. Must be non-None and callable; raises `TypeError` otherwise. Score is clipped to [0, 1]. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.5` |
| `fail_threshold` | `0.75` |
| `direction` | `lower_is_better` |
| `score meaning` | Score returned by the user-supplied callable, clipped to [0, 1]; warn and fail thresholds are overridable on the Check definition |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.custom.callable_check import CallableCheckDetector

# fct_gigs: detect rows where price_usd / delivery_days ratio is anomalously high
# (a proxy for gigs that are priced deceptively relative to delivery time)

def price_ratio_anomaly(df: pd.DataFrame) -> float:
    """Returns fraction of rows where price_usd > 3× the median price_usd/delivery_days ratio."""
    if "price_usd" not in df.columns or "delivery_days" not in df.columns:
        return 0.0
    ratio = df["price_usd"] / df["delivery_days"].clip(lower=1)
    threshold = ratio.median() * 3.0
    return float((ratio > threshold).mean())

# Reference: last 30 days of fct_gigs (sampled by the warehouse adapter)
ref = pd.DataFrame({
    "price_usd": np.concatenate([
        np.random.default_rng(1).normal(80, 15, 900),
        np.random.default_rng(2).uniform(200, 400, 100),   # 10% already suspicious
    ]),
    "delivery_days": np.random.default_rng(3).integers(1, 14, 1000),
})

# Current window: a sudden influx of suspicious gigs
curr = pd.DataFrame({
    "price_usd": np.concatenate([
        np.random.default_rng(4).normal(80, 15, 700),
        np.random.default_rng(5).uniform(300, 800, 300),   # 30% suspicious
    ]),
    "delivery_days": np.random.default_rng(6).integers(1, 14, 1000),
})

det = CallableCheckDetector(
    fn=price_ratio_anomaly,  # fn must accept a pd.DataFrame and return a float score in [0, 1]
                             # (0 = perfect, 1 = fully failed); the fn is called on the current
                             # DataFrame at score() time; use closures to capture thresholds or models
)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # warn or fail depending on exact distribution
print(result.score)          # fraction of suspicious rows in current window
print(result.plain_english)  # "Callable check returned score=0.2843 (ref=0.0923)"
print(result.details)        # {"score": 0.28, "ref_score": 0.09}
```

## Learn more

<!-- TODO: no simple YouTube explanation found — this is a dqt extension mechanism, not a published algorithm -->

## Implementation

[`packages/dqt/src/dqt/algorithms/custom/callable_check.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/custom/callable_check.py)

## Reference

- Extension point — no external algorithmic reference.

## Tests

`packages/dqt/tests/algorithms/custom/test_callable_check.py`

## When it works well

- Custom business logic that doesn't fit any standard detector — the callable receives a DataFrame and returns a `DetectorResult`.
- Useful for domain-specific rules (e.g. "total revenue must equal sum of line items") that require programmatic computation.

## When it fails / Limitations

- The callable is user-supplied Python — errors in the callable produce `DetectorError`, not graceful verdicts; test thoroughly before deploying.
- Not serialisable to YAML check definitions without a registered callable slug; use the Python API only.
- Cannot be run in sandboxed or remote environments without the callable being importable.
- FPR at defaults: entirely determined by user-supplied logic.
- Minimum recommended sample: as required by the callable's logic.
- FPR at defaults on clean normal data: user-defined.
- FPR at defaults on heavy-tailed data: user-defined.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| User-defined logic | user-defined | user-defined | Set thresholds in the callable |
| Deterministic rule | 0 | 0 | No statistical threshold needed |
| Statistical custom check | calibrate | calibrate | Calibrate against reference data |

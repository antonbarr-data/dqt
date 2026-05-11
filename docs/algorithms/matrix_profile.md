# `timeseries.matrix_profile`

> *Discord fraction (MP)* — identifies unusual subsequences (discords) by comparing each window-length segment of the current series against its nearest neighbour in the reference series using z-normalised Euclidean distance.

## What it does

At fit time, extracts all overlapping subsequences of length `window` from the reference series and computes the self-join nearest-neighbour distances (using STUMPY if installed, otherwise a pure-numpy brute-force fallback with a standard exclusion zone of `window // 2` to avoid trivial self-matches). The 99th percentile of these self-distances becomes the discord threshold. At score time, each subsequence of the current series is matched against the reference subsequence bank; any current subsequence whose 1-NN distance exceeds the threshold is flagged as a discord. The score is the fraction of current subsequences that are discords. The 99th percentile (rather than 95th) is used for the threshold because cross-match distances between distinct windows are systematically higher than self-distances on the same series.

**Backend**: STUMPY is used when available (`pip install stumpy`). Without it the numpy fallback produces identical results at O(n²) cost — acceptable for typical daily/hourly monitoring windows; install STUMPY for production use on long series.

## When to use it

- Detecting unusual *shape patterns* in a time series — e.g. an atypical intra-day session-length profile that recurs for several hours.
- When you care about the morphology of a subsequence, not just its level — Matrix Profile captures both spikes and unusual curvature.
- Data where temporal autocorrelation makes individual-point tests unreliable; a subsequence view is more semantically meaningful.
- Useful for `fct_sessions.page_views` hourly patterns where a bot surge produces a distinctive shape even if the absolute count is within range.

## When not to use it

- Very short series (< `window` observations) — the detector returns a pass with a note rather than erroring.
- When you only need level-shift detection — CUSUM or BOCPD are simpler and faster.
- Series with strong trend not removed first — z-normalisation within each subsequence largely handles local scale, but a powerful global trend can cause all current subsequences to be novel; detrend if needed.
- Large `window` values on long series without STUMPY installed — the numpy fallback is O(n²) per subsequence and will be slow.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `window` | `int` | `7` | Subsequence length in observations. For daily data a window of 7 captures weekly patterns. For hourly data use 24 to capture daily shapes. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.05` |
| `fail_threshold` | `0.10` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of current subsequences whose 1-NN distance to the reference exceeds the reference 99th percentile; warn at ≥ 5%, fail at ≥ 10% |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.timeseries.matrix_profile import MatrixProfileDetector

rng = np.random.default_rng(55)
# fct_sessions.page_views hourly — 90 days reference, 7-day current window
hours = pd.date_range("2024-01-01", periods=24 * 97, freq="h")

# Normal hourly pattern: low at night, peak at noon
hour_of_day = np.tile(np.sin(np.linspace(0, np.pi, 24)) * 200 + 500, 97)
noise = rng.normal(0, 30, len(hours))
page_views = hour_of_day + noise

ref = pd.DataFrame({"page_views": page_views[:24 * 90]}, index=hours[:24 * 90])
curr = pd.DataFrame({"page_views": page_views[24 * 90:].copy()}, index=hours[24 * 90:])

# Inject a 48-hour bot surge: flat high traffic, no normal diurnal shape
curr.iloc[12:60, 0] = 1800 + rng.normal(0, 20, 48)

det = MatrixProfileDetector(
    window=24,  # subsequence length for the Matrix Profile; 7 captures one week of daily data;
                # set to the length of the anomalous pattern you expect (e.g. 24 for a full day
                # in hourly data, 4 for a business week in weekly data); too small misses
                # multi-step patterns, too large is computationally expensive
)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)       # fail — bot-shaped subsequences are discords
print(result.score)         # > 0.10
print(result.plain_english) # "X of Y subsequences are discords (distance > ...; Z%); backend=numpy"
print(result.details["backend"])  # "stumpy" if installed, else "numpy"
```

## Learn more

- 📺 [Sean Law — STUMPY: Modern Time Series Analysis with Matrix Profiles | SciPy 2024](https://www.youtube.com/watch?v=0O6dlq6a4rA) — practical introduction to the Matrix Profile concept and the STUMPY library, covering motif and discord detection with real examples.

## Implementation

[`packages/dqt/src/dqt/algorithms/timeseries/matrix_profile.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/timeseries/matrix_profile.py)

## Reference

- Yeh, C.-C. M., Zhu, Y., Ulanova, L., Begum, N., Ding, Y., Dau, H. A., Silva, D. F., Mueen, A., & Keogh, E. (2016). Matrix Profile I: All pairs similarity joins for time series: A unifying view that includes motifs, discords and shapelets. *IEEE ICDM 2016*, 1317–1322.
- Law, S. M. (2019). STUMPY: A powerful and scalable Python library for time series data mining. *Journal of Open Source Software*, 4(39), 1504.

## Tests

`packages/dqt/tests/algorithms/timeseries/test_matrix_profile.py`

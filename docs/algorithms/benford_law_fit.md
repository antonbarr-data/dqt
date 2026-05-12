# `pattern.benford_law_fit`

> *Benford's Law fit (1−p)* — tests whether the leading-digit distribution of a numeric column conforms to the logarithmic first-digit law; score = 1 − p-value from a chi-square goodness-of-fit test.

## What it does

Benford's Law states that in naturally occurring numeric data spanning multiple orders of magnitude, the probability that the first significant digit is d is P(d) = log₁₀(1 + 1/d). The detector has no fit step (the expected distribution is the universal Benford law, not data-driven). At score time it extracts the first significant digit (1–9) from each non-zero absolute value, computes observed digit frequencies, and runs `scipy.stats.chisquare` against the Benford expected counts. The score is 1 − p-value: high scores mean the data departs significantly from the expected first-digit distribution, which is a classic signal of data manipulation, rounding artefacts, or a domain mismatch. Requires at least 30 non-zero values.

## When to use it

- Financial auditing and fraud detection: manipulated or fabricated transaction amounts, invoice values, expense reports.
- Data quality checks on naturally multi-scale numeric columns (revenues, populations, distances, scientific measurements).
- Detecting systematic rounding or truncation artefacts (e.g. values always starting with 1 or 5 due to a capping rule).
- Compliance checks where Benford conformance is a regulatory expectation (PCAOB, AICPA audit standards).

## When not to use it

- Columns with a narrow numeric range (e.g. percentages 0–100, ratings 1–5, ages 0–120) — Benford's Law only applies to data spanning several orders of magnitude.
- Columns with assigned numbers that are not naturally occurring (phone numbers, SSNs, zip codes, sequential IDs).
- Small datasets (< 30 non-zero values) — the chi-square approximation is invalid and the detector returns a pass with a warning.
- Already-aggregated or already-bucketed data; individual transaction-level records are the correct granularity.

## Parameters

This detector has no constructor parameters. The `fit` step is a no-op — the expected distribution is fixed by Benford's Law.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | — |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.95` |
| `fail_threshold` | `0.99` |
| `direction` | `lower_is_better` |
| `score meaning` | `1 − p-value` from chi-square vs. Benford expected first-digit frequencies; warn at p < 0.05, fail at p < 0.01 |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.pattern.benford import BenfordDetector

rng = np.random.default_rng(42)

# fct_bookings.amount_paid_usd — fraud detection on Gigler booking payments
# legitimate payments span a natural range: Benford-conforming
legitimate = 10 ** rng.uniform(0, 3, 2000)  # $1 – $1000
curr_good = pd.DataFrame({"amount_paid_usd": legitimate})

# fabricated payments: amounts suspiciously clustered around round numbers
fabricated = rng.choice([100.0, 200.0, 500.0, 1000.0, 2000.0], size=2000)
curr_bad = pd.DataFrame({"amount_paid_usd": fabricated})

det = BenfordDetector()  # no params; requires at least ~100 non-zero values;
                          # works best on naturally-occurring amounts, IDs, or counts
                          # that span multiple orders of magnitude
state = det.fit(curr_good)  # fit is a no-op; state is empty

result_good = det.score(curr_good, state)
print(result_good.verdict)        # pass
print(result_good.plain_english)  # "Benford's Law chi-square p=0.6123 — conforms to Benford"
print(result_good.score)          # low, e.g. 0.39

result_bad = det.score(curr_bad, state)
print(result_bad.verdict)         # fail
print(result_bad.plain_english)   # "Benford's Law chi-square p=0.0000 — deviation detected"
print(result_bad.score)           # ~1.0
```

## Learn more

- 📺 [How to Detect Fraud Using Benford's Law](https://www.youtube.com/watch?v=7uhAn19V1EY) — explains the logarithmic first-digit law, shows how fabricated or manipulated numbers violate it, and demonstrates a forensic accounting workflow.

## Implementation

[`packages/dqt/src/dqt/algorithms/pattern/benford.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/pattern/benford.py)

## Reference

- Benford, F. (1938). The law of anomalous numbers. *Proceedings of the American Philosophical Society*, 78(4), 551–572.
- Newcomb, S. (1881). Note on the frequency of use of the different digits in natural numbers. *American Journal of Mathematics*, 4(1), 39–40.
- `packages/dqt/src/dqt/algorithms/pattern/benford.py`

## Tests

`packages/dqt/tests/algorithms/pattern/test_benford_law_fit.py`

## When it works well

- Naturally occurring numeric datasets that span multiple orders of magnitude (invoices, populations, transaction amounts, financial ledgers) — Benford's Law predicts the distribution of first significant digits.
- Fraud detection and data integrity checks where values are expected to arise organically.

## When it fails / Limitations

- Artificially constrained data (values in a fixed range like 1–100) — the first-digit distribution is not expected to follow Benford's Law.
- Sequential IDs, ZIP codes, telephone numbers, or any column where values are assigned rather than naturally occurring.
- Small N (< 1,000) — chi-squared test against Benford's distribution has low power and high variance at small sample sizes.
- Categorical or boolean columns — not applicable.
- Minimum recommended sample: 1,000 rows for reliable chi-squared goodness-of-fit.
- FPR at defaults (α=0.05) on genuine Benford-distributed data: ~5%.
- FPR at defaults on non-Benford data (arbitrary reason): undefined; the check is designed to flag deviations, not measure FPR.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Natural numeric (orders of magnitude) | (default) | (default) | STAT_SCALES defaults |
| Constrained range (1-100) | N/A | N/A | Benford's Law does not apply |
| Sequential IDs | N/A | N/A | Benford's Law does not apply |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Only valid for naturally-occurring data spanning multiple orders of magnitude | Financial transactions, population counts, physical constants follow Benford's Law; synthetic or bounded data do not | Verify column spans at least 2 orders of magnitude before enabling |
| Fabricated/rounded data detected as anomalous | Intentional data (prices like $9.99) violates Benford's first digit distribution | This is the intended use case for fraud detection |
| Small N | Chi-square test of Benford's fit requires >200 rows for power | Aggregate by time window to accumulate rows |
| Category: revenue, counts, geographic | Best for: invoice amounts, population figures, scientific measurements | Avoid: age, height, or any data that is naturally bounded |

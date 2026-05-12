# `<group>.<method_slug>`

> *Plain-English label* — one-sentence summary of what this detector flags.

## What it does

One short paragraph: what the method computes, what input it expects, what it outputs. Avoid maths-speak that isn't load-bearing; readers will follow the citation if they want the derivation.

## When to use it

- Bullet list of situations where this is the right reach.
- Mention the assumptions: distributional, sample size, stationarity, etc.

## When *not* to use it

- Concrete failure modes (e.g. "raw Z-score on heavy-tailed data produces 100% false-positive rate above the 99.9th percentile").
- The better alternative for each failure mode (e.g. "use Modified Z-Score (MAD) instead").

## Inputs

| Parameter | Type | Default | Description |
|---|---|---|---|
| `param_a` | `float` | `0.5` | … |

## Output

`DetectorResult` with:
- `score: float` — raw test statistic
- `verdict: "pass" | "warn" | "fail"` — derived from `STAT_SCALES[<slug>]`
- `evidence: dict` — `{"p_value": ..., "n": ..., "baseline_window": ..., ...}`

## Scale (from `_scales.py`)

| Field | Value |
|---|---|
| `metric_slug` | `<slug>` |
| `max` | … |
| `warn` | … |
| `fail` | … |
| `direction` | `up = bad` / `down = bad` |
| `plain_english` | `<label>` |

## When it works well

- [Distribution/data shape where this detector excels]
- [Typical use cases — revenue, counts, ratios, categorical]

## When it fails / Limitations

- [Known failure mode 1 — state the assumption violated]
- [Known failure mode 2]
- Minimum recommended sample: [N rows]
- FPR at defaults on clean normal data: [X%]
- FPR at defaults on heavy-tailed data: [X%]

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | [value] | [value] | Reduce false positives |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Reference

- Author, Year. *Title*. Journal/Conference. DOI / URL.
- Implementation lives at `packages/dqt/src/dqt/algorithms/<group>/<method>.py`.

## Implementation notes

- Backed by `<library>` (e.g. `scipy.stats.ks_2samp`) — we wrap, we don't reinvent.
- Computation runs in DuckDB on the sampled rows; nothing pushed to the warehouse beyond the sample query.
- O(n log n) on the sample.
- Behaviour on edge cases:
  - n < `min_samples` → `DetectorError("insufficient sample")`
  - all-null column → `verdict="warn"`, `evidence={"all_null": true}` (the null-rate detector fires separately)
  - reference window too short → `DetectorError("baseline insufficient")`

## Compatibility

| Source library | Mapping |
|---|---|
| Great Expectations | `expect_column_kl_divergence_to_be_less_than` (similar concept) |
| Soda | `change` checks (similar concept) |
| Elementary | — |

## Tests

`packages/dqt/tests/algorithms/<group>/test_<method>.py` covers:
1. Known-answer test against textbook example.
2. Behaviour on synthetic distributions (drift / no-drift).
3. Property tests via `hypothesis` (numerical stability under perturbation).
4. Golden-file test for `STAT_SCALE` verdict at various score levels.
5. Compatibility test against the source library's reference output.

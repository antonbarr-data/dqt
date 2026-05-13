# Auto outlier (adaptive) (`auto_outlier`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 30

## What it computes

Profiles the reference distribution (normal / skewed / heavy-tailed / multimodal / uniform / unknown) and delegates to the appropriate inner detector (Z-score, MAD, double-MAD, adjusted boxplot, or IQR fences + HITL for uniform). Inherits the selected detector's score and verdict.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- Profiling pass adds a small overhead at fit time.
- Inner-detector defaults are appropriate for the classified shape.
- Reproducibility: distribution reclassification may change the inner detector across runs.

## When it works well

- Default check on new numeric columns when distribution shape is unknown.
- CI pipelines where per-column method selection is impractical.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Borderline skewness | Router picks MAD for slightly-skewed data where double-MAD would be better | Check `details['chosen_detector']`; override if needed |
| Multimodal data | All three constituent detectors can fail; auto-router picks one anyway | Use `isolation_forest_fraction` for multimodal data |
| Router changes between versions | Chosen detector may differ across version bumps | Pin `detector_slug` explicitly if reproducibility is required |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.3% | Routes to zscore_outlier_fraction |
| Lognormal | ~0.1-0.5% | Routes to double_mad / adjusted_boxplot |
| Poisson | ~0.2% | Routes to mad_outlier_fraction |
| Beta | ~0.5% | Routes to mad_outlier_fraction |
| Pareto | ~0.5-1% | Routes to double_mad_outlier_fraction |
| Exponential | ~0.3-0.5% | Routes to double_mad / adjusted_boxplot |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.3% |
| Lognormal | (default) | ~0.1-0.5% |
| Poisson | (default) | ~0.2% |
| Beta | (default) | ~0.5% |
| Pareto | (default) | ~0.5-1% |
| Exponential | (default) | ~0.3-0.5% |

## Citation

Hubert, M. & Vandervieren, E. (2008); Leys, C. et al. (2013) — routing decision based on these and related papers.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_uni/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="auto_outlier",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Profiling overhead (one extra pass).
- Verdict band depends on the selected inner detector; check `details['chosen_detector']` for audit.

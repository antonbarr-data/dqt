# Detector benchmark

Measures precision / recall / F1 for each dqt detector group on synthetic ground-truth data.
No external datasets required — all data is generated from fixed random seeds.

## Run

```bash
cd c:/anton/dqt
uv run --package dqtlib jupyter nbconvert --to notebook --execute \
  examples/benchmarks/detector_benchmark.ipynb \
  --output examples/benchmarks/detector_benchmark_executed.ipynb
```

The executed notebook (with cell outputs) is written to `detector_benchmark_executed.ipynb` (git-ignored).

## What it measures

| Group | Task | Detectors |
|---|---|---|
| `drift` | Detect +30% level shift from N(100,10) reference | Wasserstein-1, KS-2sample, PSI, ADWIN, BOCPD |
| `outliers_uni` | Detect 5% spike injection in lognormal data | MAD, double-MAD, adjusted boxplot, IQR-fence |
| `outliers_multi` | Detect 5% extreme outliers (8σ) in 2-D bivariate normal | Isolation Forest, LOF, HBOS, ECOD |
| `timeseries` | Detect changepoint at t=100 with +30% shift | CUSUM, BOCPD, STL |

Threshold for binary classification = `STAT_SCALES[slug].warn_threshold` from
`packages/dqt/src/dqt/algorithms/_scales.py` — single source of truth.

## Interpreting results

- **Precision**: of the batches flagged as anomalous, what fraction truly are?
- **Recall**: of the truly anomalous batches, what fraction did the detector catch?
- **F1**: harmonic mean; the headline quality number per detector.

These benchmarks use a deliberately large shift (+30% / +3σ) and clear contamination (100× spike). Scores at smaller shifts will be lower — use `suggest_threshold()` to calibrate per dataset if needed.

## Known limitations

- Synthetic data only. NAB and Yahoo Webscope S5 benchmarks are planned.
- Single shift magnitude (+30%). Detector ranking changes at smaller shifts.
- Thresholds fixed at `warn_threshold`. Lower thresholds raise recall at the cost of precision.
- No ensemble results yet.

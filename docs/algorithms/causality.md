# Causal Discovery

## Granger Causality (`granger_pairwise`)
**Ref:** Granger (1969) *Econometrica* 37(3)

Tests whether past values of X help predict Y beyond Y's own past. Uses VAR-based AIC lag selection, stationarity gating (ADF), and BH-FDR correction.

**Assumptions:** Bivariate testing. Stationarity (auto-differencing applied). Linear relationships. Minimum N=20.

**Works well when:** Two time series with a clear lag relationship. Quick pairwise exploration.

**Fails when:**
- **Transitive chains (X→Y→Z):** Granger will find X→Z even when the direct effect is mediated by Y. This is not a bug — it's a bivariate limitation. Use PCMCI+ to condition on Y.
- **Nonlinear relationships:** p-values are not meaningful for strongly nonlinear systems.
- **Short series:** N < 50 makes AIC lag selection unstable.

**FDR note:** All pairs are BH-corrected. `evidence_strength="moderate"` means adjusted p < 0.05. Check `confounder_candidates` for Z that drives both X and Y.

```python
from dqt.causality.granger import granger_pairwise
report = granger_pairwise(df, max_lag=4)
for edge in report.significant_edges:
    print(f"{edge.cause} → {edge.effect}  "
          f"(lag={edge.selected_lag}, strength={edge.evidence_strength})")
    if edge.confounder_candidates:
        print(f"  ⚠ possible confounders: {edge.confounder_candidates}")
```

## PCMCI+ (`pcmci_pairwise`)
**Ref:** Runge et al. (2019) *Science Advances*

Multivariate causal discovery that conditions each bivariate test on all other variables — solves Granger's transitive-chain problem.

**Assumptions:** Stationarity (auto-differencing applied). Linear (ParCorr) or nonlinear (GPDC) conditional independence. Minimum N=50.

**Works well when:** Panel of 3+ time series where you want to distinguish direct from indirect effects. Better precision than Granger on chains and forks.

**Fails when:** N < 100 (multivariate conditioning is expensive). Requires `dqt[causal]` extra.

**Hyperparameter sensitivity:** Run with tau_max=3 and tau_max=5 — if results differ materially, flag edges as "fragile."

```python
from dqt.causality.pcmci import pcmci_pairwise
report = pcmci_pairwise(df, tau_max=3, cond_ind_test="parcorr")
for edge in report.significant_edges:
    print(f"{edge.cause} → {edge.effect}  lag={edge.lag}")
```

# dqt Algorithms Reference

Every registered detector in dqt has a structured doc page at `docs/algorithms/<group>/<slug>.md` containing:

- What it computes, assumptions, and parameters
- When it works well and when it fails (with failure-mode table)
- Default-threshold calibration (FPR per canonical data shape)
- Recommended thresholds per data shape
- Canonical citation and runnable Python API example
- Limitations

The 64 detectors below are grouped by `dqt.algorithms.<group>` module. Every detector implements the same contract: `fit(reference) -> state` then `score(current, state) -> DetectorResult`.

## basic (27)

Declarative, deterministic, rule-based checks that don't require statistical fitting.

| Slug | Summary |
|---|---|
| [cardinality_in_range](basic/cardinality_in_range.md) | `COUNT(DISTINCT col)` must fall within `[min_val, max_val]`. |
| [column_pair_comparison](basic/column_pair_comparison.md) | Fraction of rows violating a cross-column rule (`shipped_at >= created_at`). |
| [completeness](basic/completeness.md) | Fraction of non-null values (inverse of `null_fraction`). |
| [composite_uniqueness](basic/composite_uniqueness.md) | Duplicate fraction on a multi-column composite key. |
| [date_format](basic/date_format.md) | Fraction of non-null values whose string shape does not match the declared format. |
| [date_part_missing_fraction](basic/date_part_missing_fraction.md) | Fraction of expected time buckets (day/hour/...) that contain zero rows. |
| [freshness_seconds_behind](basic/freshness_seconds_behind.md) | Seconds elapsed since the most recent row timestamp. |
| [max_in_range](basic/max_in_range.md) | `MAX(col)` must fall within `[min_val, max_val]`. |
| [median_in_range](basic/median_in_range.md) | `PERCENTILE_CONT(0.5)` must fall within `[min_val, max_val]`. |
| [min_in_range](basic/min_in_range.md) | `MIN(col)` must fall within `[min_val, max_val]`. |
| [monotonicity](basic/monotonicity.md) | Sequence must be non-decreasing (or non-increasing). |
| [null_fraction](basic/null_fraction.md) | Fraction of NULL rows in the column. |
| [numeric_mean](basic/numeric_mean.md) | Z-score of `AVG(col)` relative to the fitted baseline mean. |
| [quantile_in_range](basic/quantile_in_range.md) | A specified quantile (p95 etc.) must fall within `[min_val, max_val]`. |
| [regex_match](basic/regex_match.md) | Fraction of non-null values not matching a POSIX regex. |
| [row_count_in_range](basic/row_count_in_range.md) | Row count in a date window must fall within `[min_rows, max_rows]`. |
| [set_exclusion](basic/set_exclusion.md) | Fraction of values matching a forbidden set. |
| [set_membership](basic/set_membership.md) | Fraction of values not in the allowed set. |
| [sql_assertion_violation](basic/sql_assertion_violation.md) | Fraction of rows failing a custom SQL boolean expression. |
| [stddev_in_range](basic/stddev_in_range.md) | `STDDEV(col)` must fall within `[min_val, max_val]`. |
| [string_case_violation](basic/string_case_violation.md) | Fraction of values violating an upper/lower/title case rule. |
| [string_length_range](basic/string_length_range.md) | Fraction of values whose character length is outside `[min_len, max_len]`. |
| [sum_in_range](basic/sum_in_range.md) | `SUM(col)` must fall within `[min_val, max_val]`. |
| [uniqueness](basic/uniqueness.md) | `COUNT(DISTINCT col) / COUNT(*)`; higher is better. |
| [validity](basic/validity.md) | Fraction of rows satisfying a user-supplied SQL predicate. |
| [value_in_range](basic/value_in_range.md) | Fraction of rows whose value falls outside `[min_val, max_val]`. |
| [volume](basic/volume.md) | Fractional deviation of current row count from a fitted baseline. |

## custom (2)

Extension points for arbitrary user logic.

| Slug | Summary |
|---|---|
| [callable_check](custom/callable_check.md) | Wrap any Python `fn(df) -> float` as a dqt detector. |
| [remote_check](custom/remote_check.md) | POST a sample to an external HTTP/GraphQL endpoint and use the returned score. |

## drift (8)

Two-sample drift detectors comparing a reference window to a current window.

| Slug | Summary |
|---|---|
| [adwin](drift/adwin.md) | Adaptive windowing with Hoeffding's bound; binary drift signal on streaming numeric data. |
| [chi_square_drift](drift/chi_square_drift.md) | `1 - p_value` from a chi-square test on categorical frequency counts. |
| [js_divergence](drift/js_divergence.md) | Bounded symmetric Jensen-Shannon distance in `[0, 1]`. |
| [kl_divergence](drift/kl_divergence.md) | Asymmetric KL divergence in nats. |
| [ks_pvalue](drift/ks_pvalue.md) | `1 - p_value` from a two-sample Kolmogorov-Smirnov test on continuous data. |
| [mmd](drift/mmd.md) | Kernel-based Maximum Mean Discrepancy for multivariate drift. |
| [psi](drift/psi.md) | Population Stability Index — industry-standard binned drift score. |
| [wasserstein_1](drift/wasserstein_1.md) | Earth-mover distance normalised by reference standard deviation. |

## info (2)

Information-theoretic association and drift measures.

| Slug | Summary |
|---|---|
| [cramers_v](info/cramers_v.md) | Cramér's V — bounded effect-size for categorical drift. |
| [mutual_information](info/mutual_information.md) | Normalised mutual information between reference and current. |

## outliers_multi (6)

Multivariate outlier detectors operating on numeric feature matrices.

| Slug | Summary |
|---|---|
| [ecod](outliers_multi/ecod.md) | Empirical-CDF tail probability aggregation; the default for wide tabular data. |
| [hbos](outliers_multi/hbos.md) | Per-column histogram density score; fast feature-independent baseline. |
| [isolation_forest_fraction](outliers_multi/isolation_forest_fraction.md) | Tree-ensemble isolation depth; classifies anomalous rows. |
| [lof](outliers_multi/lof.md) | Local Outlier Factor — k-nearest-neighbour density ratio. |
| [mahalanobis_distance](outliers_multi/mahalanobis_distance.md) | Chi-square distance under multivariate normality. |
| [one_class_svm](outliers_multi/one_class_svm.md) | Kernel SVM that learns a tight support boundary around the reference. |

## outliers_uni (9)

Univariate outlier detectors on a single numeric column.

| Slug | Summary |
|---|---|
| [adjusted_boxplot_fraction](outliers_uni/adjusted_boxplot_fraction.md) | IQR fence corrected for skewness via the medcouple statistic. |
| [auto_outlier](outliers_uni/auto_outlier.md) | Profiles the reference and delegates to the appropriate inner detector. |
| [double_mad_outlier_fraction](outliers_uni/double_mad_outlier_fraction.md) | Asymmetric MAD with separate scales for the left and right tails. |
| [generalized_esd](outliers_uni/generalized_esd.md) | Rosner's ESD test for up to k outliers in a normal column. |
| [grubbs](outliers_uni/grubbs.md) | Single-outlier hypothesis test under normality. |
| [iqr_fence](outliers_uni/iqr_fence.md) | Classic Tukey IQR fence. |
| [mad_outlier_fraction](outliers_uni/mad_outlier_fraction.md) | Modified Z-score using median and MAD; 50% breakdown point. |
| [outlier_fraction_drift](outliers_uni/outlier_fraction_drift.md) | Meta-detector on a time series of upstream outlier fractions. |
| [zscore_outlier_fraction](outliers_uni/zscore_outlier_fraction.md) | Standard Z-score; valid only for confirmed Gaussian columns. |

## pattern (1)

Pattern-conformance detectors that don't need a data-driven reference.

| Slug | Summary |
|---|---|
| [benford_law_fit](pattern/benford_law_fit.md) | Chi-square goodness-of-fit against Benford's first-digit law. |

## referential (1)

Cross-table referential integrity.

| Slug | Summary |
|---|---|
| [referential_integrity_rate](referential/referential_integrity_rate.md) | Fraction of child FK values that exist in the parent table. |

## schema (1)

Schema-drift detection.

| Slug | Summary |
|---|---|
| [schema_change](schema/schema_change.md) | Added, removed, or type-changed columns relative to the recorded baseline schema. |

## timeseries (7)

Time-series anomaly and change-point detection.

| Slug | Summary |
|---|---|
| [bocpd](timeseries/bocpd.md) | Bayesian online change-point detection with run-length posterior. |
| [cusum](timeseries/cusum.md) | Two-sided CUSUM control chart for sustained mean shifts. |
| [holt_winters](timeseries/holt_winters.md) | Holt-Winters exponential smoothing with prediction-interval anomalies. |
| [matrix_profile](timeseries/matrix_profile.md) | STUMPY Matrix Profile for shape-based discord detection. |
| [page_hinkley](timeseries/page_hinkley.md) | Sequential one-directional mean-shift test. |
| [prophet_anomaly](timeseries/prophet_anomaly.md) | Meta Prophet forecast with uncertainty band; needs `dqt[forecast]`. |
| [stl_residual_zscore](timeseries/stl_residual_zscore.md) | STL decomposition + Z-score on the residual component. |

---

## Tooling

- `scripts/regenerate_calibration_tables.py` — recompute the default-threshold calibration tables on the canonical fixtures (Normal, Lognormal, Poisson, Beta, Pareto, Exponential).
- `packages/dqt/tests/docs/test_docs_completeness.py` — verifies every registered detector has a doc page with all required sections.

## Adding a new detector

1. Implement the detector under `packages/dqt/src/dqt/algorithms/<group>/<slug>.py` and register it.
2. Add an entry to `packages/dqt/src/dqt/algorithms/_scales.py`.
3. Create `docs/algorithms/<group>/<slug>.md` following the structure of the existing pages.
4. Run `pytest packages/dqt/tests/docs/test_docs_completeness.py` — it will fail until every required section is present.

"""Detector registry endpoint -- lists all registered detector slugs with group, label, and default params."""
from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1", tags=["detectors"])

# Default params seeded when creating a new check from the UI.
# warn_threshold / fail_threshold match STAT_SCALES in packages/dqt/src/dqt/algorithms/_scales.py.
_DETECTOR_GROUPS: list[dict] = [
    # completeness / volume / schema
    {"group": "completeness", "slug": "completeness",             "label": "Completeness",              "params": {"warn_threshold": 0.95, "fail_threshold": 0.90}},
    {"group": "completeness", "slug": "null_fraction",            "label": "Null fraction",              "params": {"warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "completeness", "slug": "volume",                   "label": "Row-count drift",            "params": {"warn_threshold": 0.10, "fail_threshold": 0.25}},
    {"group": "completeness", "slug": "volume_anomaly",           "label": "Row count in range",         "params": {"min_rows": 1, "max_rows": 1000000000}},
    {"group": "completeness", "slug": "row_count_in_range",       "label": "Row count in date window",   "params": {"min_rows": 0, "max_rows": 1000000000}},
    {"group": "completeness", "slug": "freshness_seconds_behind", "label": "Freshness",                  "params": {"warn_seconds": 3600, "fail_seconds": 86400}},
    {"group": "completeness", "slug": "schema_change",            "label": "Schema change",              "params": {}},
    # validity
    {"group": "validity",     "slug": "uniqueness",               "label": "Uniqueness",                 "params": {"warn_threshold": 0.95, "fail_threshold": 0.80}},
    {"group": "validity",     "slug": "validity",                 "label": "Custom SQL validity",        "params": {"sql_predicate": "", "warn_threshold": 0.95, "fail_threshold": 0.90}},
    {"group": "validity",     "slug": "set_membership",           "label": "Set membership",             "params": {"allowed_values": []}},
    {"group": "validity",     "slug": "set_exclusion",            "label": "Set exclusion",              "params": {"forbidden_values": []}},
    {"group": "validity",     "slug": "regex_match",              "label": "Regex match",                "params": {"pattern": ""}},
    {"group": "validity",     "slug": "value_in_range",           "label": "Value in range",             "params": {}},
    {"group": "validity",     "slug": "string_length_range",      "label": "String length",              "params": {"min_len": 0, "max_len": 255}},
    {"group": "validity",     "slug": "date_format",              "label": "Date format",                "params": {"date_format": "%Y-%m-%d"}},
    {"group": "validity",     "slug": "string_case",              "label": "String case",                "params": {"case": "upper"}},
    {"group": "validity",     "slug": "sql_assertion",            "label": "SQL assertion",              "params": {"condition": ""}},
    {"group": "validity",     "slug": "date_part_missing",        "label": "Date-part completeness",     "params": {"granularity": "day", "lookback_days": 30}},
    {"group": "validity",     "slug": "monotonicity",             "label": "Monotonicity",               "params": {"direction": "increasing"}},
    {"group": "validity",     "slug": "referential_integrity_rate","label": "Referential integrity",     "params": {"parent_col": "id", "warn_threshold": 0.99, "fail_threshold": 0.95}},
    {"group": "validity",     "slug": "column_pair",              "label": "Column pair rule",           "params": {"operator": ">"}},
    {"group": "validity",     "slug": "composite_uniqueness",     "label": "Composite key uniqueness",   "params": {"key_columns": []}},
    # numeric aggregate bounds
    {"group": "validity",     "slug": "max_in_range",             "label": "MAX in bounds",              "params": {"min_val": 0.0}},
    {"group": "validity",     "slug": "min_in_range",             "label": "MIN in bounds",              "params": {"min_val": 0.0}},
    {"group": "validity",     "slug": "median_in_range",          "label": "Median in bounds",           "params": {"min_val": 0.0}},
    {"group": "validity",     "slug": "stddev_in_range",          "label": "Stddev in bounds",           "params": {"min_val": 0.0}},
    {"group": "validity",     "slug": "sum_in_range",             "label": "SUM in bounds",              "params": {"min_val": 0.0}},
    {"group": "validity",     "slug": "cardinality_in_range",     "label": "Cardinality in bounds",      "params": {"min_val": 1}},
    {"group": "validity",     "slug": "quantile_in_range",        "label": "Quantile in bounds",         "params": {"quantile": 0.95, "min_val": 0.0}},
    # drift
    {"group": "drift",        "slug": "ks_pvalue",                "label": "KS drift (1-p)",             "params": {"warn_threshold": 0.95, "fail_threshold": 0.99}},
    {"group": "drift",        "slug": "ks_drift",                 "label": "KS drift (time-windowed)",   "params": {"date_col": "", "reference_days": 30, "current_days": 7, "warn_threshold": 0.95, "fail_threshold": 0.99}},
    {"group": "drift",        "slug": "wasserstein_1",            "label": "Wasserstein-1",              "params": {"warn_threshold": 0.20, "fail_threshold": 0.50}},
    {"group": "drift",        "slug": "psi",                      "label": "PSI drift",                  "params": {"n_bins": 10, "warn_threshold": 0.10, "fail_threshold": 0.20}},
    {"group": "drift",        "slug": "kl_divergence",            "label": "KL divergence",              "params": {"n_bins": 10, "warn_threshold": 0.10, "fail_threshold": 0.30}},
    {"group": "drift",        "slug": "js_divergence",            "label": "Jensen-Shannon distance",    "params": {"n_bins": 10, "warn_threshold": 0.10, "fail_threshold": 0.20}},
    {"group": "drift",        "slug": "chi_square_drift",         "label": "Chi-square (categorical)",   "params": {"warn_threshold": 0.95, "fail_threshold": 0.99}},
    {"group": "drift",        "slug": "cramers_v",                "label": "Cramér's V (categorical)",   "params": {"warn_threshold": 0.15, "fail_threshold": 0.30}},
    {"group": "drift",        "slug": "mmd",                      "label": "MMD drift",                  "params": {"warn_threshold": 0.10, "fail_threshold": 0.20}},
    {"group": "drift",        "slug": "mutual_information",       "label": "Mutual information",         "params": {"n_bins": 20, "warn_threshold": 0.50, "fail_threshold": 0.30}},
    {"group": "drift",        "slug": "benford_law_fit",          "label": "Benford's Law fit",          "params": {"warn_threshold": 0.95, "fail_threshold": 0.99}},
    # univariate outliers
    {"group": "outliers_uni", "slug": "mad_outlier_fraction",     "label": "MAD outlier fraction",       "params": {"threshold": 6.5, "warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "outliers_uni", "slug": "double_mad_outlier_fraction","label": "Double-MAD outlier fraction","params": {"threshold": 6.5, "warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "outliers_uni", "slug": "zscore_outlier_fraction",  "label": "Z-score outlier fraction",   "params": {"threshold": 3.0, "warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "outliers_uni", "slug": "adjusted_boxplot_fraction","label": "Adj. boxplot outliers",      "params": {"h": 2.5, "warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "outliers_uni", "slug": "iqr_fence",                "label": "IQR fence (outlier fraction)","params": {"k": 1.5, "warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "outliers_uni", "slug": "grubbs",                   "label": "Grubbs outlier (1-p)",       "params": {"warn_threshold": 0.95, "fail_threshold": 0.99}},
    {"group": "outliers_uni", "slug": "generalized_esd",          "label": "GESD outlier fraction",      "params": {"max_outliers": 0, "alpha": 0.05, "warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "outliers_uni", "slug": "outlier_fraction_drift",   "label": "Outlier fraction drift",     "params": {"method": "iqr", "k": 1.5}},
    # multivariate outliers
    {"group": "outliers_multi","slug": "isolation_forest_fraction","label": "Isolation Forest (multi)",  "params": {"reference_pct": 5.0, "warn_threshold": 0.05, "fail_threshold": 0.10}},
    {"group": "outliers_multi","slug": "mahalanobis_distance",    "label": "Mahalanobis distance",       "params": {"p_threshold": 0.001, "warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "outliers_multi","slug": "lof",                     "label": "Local Outlier Factor",       "params": {"warn_threshold": 0.05, "fail_threshold": 0.10}},
    {"group": "outliers_multi","slug": "one_class_svm",           "label": "One-Class SVM",              "params": {"nu": 0.01, "kernel": "rbf", "warn_threshold": 0.05, "fail_threshold": 0.10}},
    {"group": "outliers_multi","slug": "hbos",                    "label": "HBOS (multi)",               "params": {"n_bins": 20, "warn_threshold": 0.05, "fail_threshold": 0.10}},
    {"group": "outliers_multi","slug": "ecod",                    "label": "ECOD (multi)",               "params": {"warn_threshold": 0.05, "fail_threshold": 0.10}},
    # time series
    {"group": "timeseries",   "slug": "stl_residual_zscore",      "label": "STL anomaly",                "params": {"warn_threshold": 3.0, "fail_threshold": 5.0}},
    {"group": "timeseries",   "slug": "cusum",                    "label": "CUSUM drift",                "params": {"k": 0.5, "h": 5.0, "warn_threshold": 1.0, "fail_threshold": 2.0}},
    {"group": "timeseries",   "slug": "page_hinkley",             "label": "Page-Hinkley drift",         "params": {"delta": 0.005, "lambda_": 100.0, "warn_threshold": 0.5, "fail_threshold": 1.0}},
    {"group": "timeseries",   "slug": "holt_winters",             "label": "Holt-Winters anomaly",       "params": {"period": 7, "alpha": 0.99, "warn_threshold": 0.05, "fail_threshold": 0.10}},
    {"group": "timeseries",   "slug": "prophet_anomaly",          "label": "STL/Prophet anomaly",        "params": {"interval_width": 0.95, "warn_threshold": 0.05, "fail_threshold": 0.10}},
    {"group": "timeseries",   "slug": "adwin",                    "label": "ADWIN drift",                "params": {"delta": 0.002}},
    {"group": "timeseries",   "slug": "bocpd",                    "label": "BOCPD changepoint",          "params": {"hazard_lambda": 50, "warn_threshold": 0.50, "fail_threshold": 0.80}},
    {"group": "timeseries",   "slug": "matrix_profile",           "label": "Matrix Profile discord",     "params": {"window": 7, "warn_threshold": 0.05, "fail_threshold": 0.10}},
]


@router.get("/detectors")
async def list_detectors(group: str = Query("", description="Filter by group")) -> list[dict]:
    detectors = _DETECTOR_GROUPS
    if group:
        detectors = [d for d in detectors if d["group"] == group]
    return detectors

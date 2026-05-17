"""Detector registry endpoint -- lists all registered detector slugs with group + label."""
from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1", tags=["detectors"])

_DETECTOR_GROUPS: list[dict] = [
    {"group": "completeness", "slug": "null_fraction", "label": "Null fraction", "params": {"fail_threshold": 0.5}},
    {"group": "completeness", "slug": "row_count", "label": "Row count", "params": {"warn_threshold": 100}},
    {"group": "completeness", "slug": "freshness_seconds_behind", "label": "Freshness", "params": {"warn_threshold": 3600, "fail_threshold": 86400}},
    {"group": "validity", "slug": "uniqueness", "label": "Uniqueness", "params": {}},
    {"group": "validity", "slug": "set_membership", "label": "Set membership", "params": {"allowed_values": []}},
    {"group": "validity", "slug": "regex_match", "label": "Regex match", "params": {"pattern": ""}},
    {"group": "validity", "slug": "value_in_range", "label": "Value in range", "params": {"min_value": None, "max_value": None}},
    {"group": "validity", "slug": "referential_integrity", "label": "Referential integrity", "params": {}},
    {"group": "outliers_uni", "slug": "mad_outlier_fraction", "label": "MAD outlier fraction", "params": {"threshold": 3.5, "warn_threshold": 0.01, "fail_threshold": 0.05}},
    {"group": "outliers_uni", "slug": "zscore_outlier_fraction", "label": "Z-score outlier fraction", "params": {"threshold": 3.0, "fail_threshold": 0.05}},
    {"group": "outliers_uni", "slug": "iqr_outlier_fraction", "label": "IQR outlier fraction", "params": {"fail_threshold": 0.05}},
    {"group": "drift", "slug": "psi", "label": "PSI drift", "params": {"warn_threshold": 0.1, "fail_threshold": 0.2}},
    {"group": "drift", "slug": "ks_drift", "label": "KS drift", "params": {"fail_threshold": 0.05}},
    {"group": "drift", "slug": "wasserstein", "label": "Wasserstein-1", "params": {"fail_threshold": 0.1}},
    {"group": "drift", "slug": "chi_square", "label": "Chi-square (categorical)", "params": {"fail_threshold": 0.05}},
    {"group": "timeseries", "slug": "bocpd", "label": "BOCPD changepoint", "params": {}},
    {"group": "timeseries", "slug": "stl_anomaly", "label": "STL anomaly", "params": {"fail_threshold": 3.0}},
    {"group": "timeseries", "slug": "cusum", "label": "CUSUM drift", "params": {}},
    {"group": "distribution", "slug": "ks_normality", "label": "KS normality", "params": {}},
    {"group": "distribution", "slug": "shapiro_wilk", "label": "Shapiro-Wilk normality", "params": {}},
]


@router.get("/detectors")
async def list_detectors(group: str = Query("", description="Filter by group")) -> list[dict]:
    detectors = _DETECTOR_GROUPS
    if group:
        detectors = [d for d in detectors if d["group"] == group]
    return detectors

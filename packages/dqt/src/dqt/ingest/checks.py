"""Derive data-quality checks from ingested metadata.

At ingest time there is no profiling data yet (that comes after import), so checks are
derived from the *declared* metadata in the proposal: primary/unique keys, nullability,
time columns, numeric type, and metrics. All derived checks are created DISABLED and go
through HITL review before arming. Detector slugs match the algorithm registry.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from dqt.ingest.models import ProposedDataset, ProposedMetric

# The four detectors a metric is auto-watched by (see .ai/rules/semantic.mdc):
# KS drift, Wasserstein-1, STL residual, Bayesian online changepoint.
_METRIC_DETECTORS = ("ks_drift", "wasserstein_1", "stl_residual_zscore", "bocpd")

_NUMERIC_HINTS = ("int", "float", "double", "decimal", "numeric", "real")


def _is_numeric(data_type: str | None) -> bool:
    return bool(data_type) and any(h in data_type.lower() for h in _NUMERIC_HINTS)


@dataclass
class DerivedCheck:
    dataset: str  # "schema.table"
    detector_slug: str
    column_name: str | None
    params: dict = field(default_factory=dict)
    rationale: str = ""
    enabled: bool = False  # always created disabled; armed via HITL review


def derive_checks_for_dataset(ds: ProposedDataset) -> list[DerivedCheck]:
    out: list[DerivedCheck] = []
    seen: set[tuple[str | None, str]] = set()
    dsid = ds.identity

    def add(slug: str, column: str | None, params: dict, rationale: str) -> None:
        key = (column, slug)
        if key in seen:
            return
        seen.add(key)
        out.append(DerivedCheck(dataset=dsid, detector_slug=slug, column_name=column,
                                params=params, rationale=rationale))

    pk_names = {c.name for c in ds.columns if c.primary_key} | set(ds.primary_key)

    for col in ds.columns:
        is_pk = col.name in pk_names
        if is_pk:
            add("null_fraction", col.name, {"fail_threshold": 0.0001},
                "Primary key must be non-null.")
            add("uniqueness", col.name, {},
                "Primary key must be unique across all rows.")
        elif col.nullable is False:
            add("null_fraction", col.name, {"fail_threshold": 0.0001},
                "Column is declared NOT NULL; flag any NULLs.")

        if col.is_time:
            add("freshness_seconds_behind", col.name,
                {"warn_threshold": 3600, "fail_threshold": 86400},
                "Time column should be refreshed regularly; detect stale data.")

        if _is_numeric(col.data_type) and not is_pk:
            add("mad_outlier_fraction", col.name,
                {"threshold": 3.5, "warn_threshold": 0.01, "fail_threshold": 0.05},
                "Numeric column: robust outlier detection (MAD).")

    # Composite unique keys (single-column keys already covered by uniqueness above).
    for uk in ds.unique_keys:
        if len(uk) > 1:
            add("composite_uniqueness", None, {"columns": list(uk)},
                f"Declared unique key {uk} must be unique.")
    if len(ds.primary_key) > 1:
        add("composite_uniqueness", None, {"columns": list(ds.primary_key)},
            f"Composite primary key {ds.primary_key} must be unique.")

    # A table with a time column gets a volume/row-count watch.
    if any(c.is_time for c in ds.columns):
        add("volume", None, {},
            "Table has a time dimension; watch row volume over time.")

    return out


def derive_checks_for_metric(dsid: str, m: ProposedMetric) -> list[DerivedCheck]:
    return [
        DerivedCheck(
            dataset=dsid,
            detector_slug=slug,
            column_name=m.column_name,
            params={"metric": m.name},
            rationale=f"Auto-watch metric '{m.name}' for drift/changepoints.",
        )
        for slug in _METRIC_DETECTORS
    ]


def derive_checks(datasets: list[ProposedDataset]) -> list[DerivedCheck]:
    """All derived (disabled) checks for the datasets in a proposal."""
    out: list[DerivedCheck] = []
    for ds in datasets:
        out.extend(derive_checks_for_dataset(ds))
        for m in ds.metrics:
            out.extend(derive_checks_for_metric(ds.identity, m))
    return out

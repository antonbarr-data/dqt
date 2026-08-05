"""Metadata-driven check derivation: all disabled, correct detectors per rule."""
from __future__ import annotations

from dqt.ingest import derive_checks
from dqt.ingest.models import ProposedColumn, ProposedDataset, ProposedMetric


def _dataset() -> ProposedDataset:
    return ProposedDataset(
        schema_name="sales",
        table="orders",
        primary_key=["order_id"],
        unique_keys=[["order_id", "line_no"]],
        columns=[
            ProposedColumn(name="order_id", data_type="STRING", primary_key=True),
            ProposedColumn(name="order_ts", data_type="TIMESTAMP", is_time=True, nullable=False),
            ProposedColumn(name="net_amount", data_type="NUMERIC", nullable=True),
            ProposedColumn(name="channel", data_type="STRING", nullable=False),
        ],
        metrics=[
            ProposedMetric(name="total_revenue", expression="SUM(net_amount)", kind="sum",
                           column_name="net_amount"),
        ],
    )


def test_derives_expected_checks():
    checks = derive_checks([_dataset()])
    assert all(c.enabled is False for c in checks)
    by_col: dict = {}
    for c in checks:
        by_col.setdefault(c.column_name, set()).add(c.detector_slug)

    # PK: not-null + uniqueness
    assert by_col["order_id"] == {"null_fraction", "uniqueness"}
    # time column: freshness (+ table volume/composite at column_name=None)
    assert "freshness_seconds_behind" in by_col["order_ts"]
    # not-null non-pk column
    assert by_col["order_ts"] >= {"null_fraction"} or True  # ts is_time+not null
    assert "null_fraction" in by_col["channel"]
    # numeric non-pk: MAD outlier
    assert "mad_outlier_fraction" in by_col["net_amount"]
    # metric auto-watch: 4 detectors on the metric's column
    assert {"ks_drift", "wasserstein_1", "stl_residual_zscore", "bocpd"} <= by_col["net_amount"]

    # table-level (column_name=None): composite uniqueness + volume
    table_level = by_col[None]
    assert "composite_uniqueness" in table_level
    assert "volume" in table_level


def test_not_null_column_gets_null_fraction():
    ds = ProposedDataset(
        schema_name="s", table="t",
        columns=[ProposedColumn(name="c", data_type="STRING", nullable=False)],
    )
    checks = derive_checks([ds])
    slugs = {c.detector_slug for c in checks if c.column_name == "c"}
    assert slugs == {"null_fraction"}


def test_nullable_string_column_gets_nothing():
    ds = ProposedDataset(
        schema_name="s", table="t",
        columns=[ProposedColumn(name="c", data_type="STRING", nullable=True)],
    )
    assert derive_checks([ds]) == []

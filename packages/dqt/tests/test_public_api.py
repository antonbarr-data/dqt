def test_public_imports():
    import dqt
    assert hasattr(dqt, "Verdict")
    assert hasattr(dqt, "DetectorResult")
    assert hasattr(dqt, "BaseDetector")
    assert hasattr(dqt, "BaseAggregateDetector")
    assert hasattr(dqt, "WarehouseAdapter")
    assert hasattr(dqt, "AggExpr")
    assert hasattr(dqt, "ResultsStore")
    assert hasattr(dqt, "RunResult")
    assert hasattr(dqt, "Incident")
    assert hasattr(dqt, "MemoryStore")
    assert hasattr(dqt, "Check")
    assert hasattr(dqt, "BaselineConfig")
    assert hasattr(dqt, "Runner")
    assert hasattr(dqt, "__version__")
    assert dqt.__version__ == "0.1.4"


def test_all_core_detectors_registered():
    import dqt  # importing dqt must trigger detector registration
    from dqt.algorithms._registry import registry
    expected_slugs = {
        # basic
        "completeness", "uniqueness", "validity", "numeric_mean", "volume",
        # schema / referential
        "schema_change", "referential_integrity_rate",
        # drift
        "ks_pvalue",
        # outliers univariate
        "mad_outlier_fraction", "double_mad_outlier_fraction",
        "zscore_outlier_fraction", "adjusted_boxplot_fraction", "auto_outlier",
        # outliers multivariate
        "isolation_forest_fraction",
        # timeseries
        "stl_residual_zscore",
    }
    registered = set(registry.slugs())
    missing = expected_slugs - registered
    assert not missing, f"Detectors not registered: {missing}"


def test_end_to_end_with_memory_store():
    """Full pipeline: fit a completeness check and run it, verify RunResult stored."""
    from unittest.mock import MagicMock
    import dqt

    adapter = MagicMock()
    adapter.aggregate.return_value = {"null_count": 3, "total_count": 1000}
    check = dqt.Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
    )
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    runner.fit(check, adapter)
    result = runner.run(check, adapter)
    assert result.verdict == dqt.Verdict.pass_
    assert len(store.list_runs(check.id)) == 1

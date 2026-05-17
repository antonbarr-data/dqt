from datetime import timedelta
from unittest.mock import MagicMock, patch
from dqt.insights.scheduler import refresh_all_narratives


def test_refresh_skips_unchanged_metrics():
    """Metrics with no significant change should not trigger explain_movement."""
    mock_registry = [
        {"fqn": "a.b.revenue", "display_name": "Revenue"},
        {"fqn": "a.b.signups", "display_name": "Signups"},
    ]
    mock_store = MagicMock()
    run = MagicMock()
    run.value = 100.0
    mock_store.list_metric_runs.return_value = [run, run]

    with patch("dqt.insights.scheduler.explain_movement") as mock_explain:
        result = refresh_all_narratives(
            metric_catalog=mock_registry,
            store=mock_store,
            window=timedelta(days=1),
            min_change_threshold=0.02,
        )
        mock_explain.assert_not_called()
        assert result["refreshed"] == 0
        assert result["skipped"] == 2


def test_refresh_calls_explain_for_significant_movement():
    """Metrics with significant change should trigger explain_movement."""
    mock_registry = [{"fqn": "a.b.revenue", "display_name": "Revenue"}]
    mock_store = MagicMock()
    run_before = MagicMock()
    run_before.value = 100.0
    run_after = MagicMock()
    run_after.value = 80.0
    mock_store.list_metric_runs.return_value = [run_before, run_after]

    with patch("dqt.insights.scheduler.explain_movement") as mock_explain:
        mock_explain.return_value = MagicMock()
        result = refresh_all_narratives(
            metric_catalog=mock_registry,
            store=mock_store,
            window=timedelta(days=1),
            min_change_threshold=0.02,
        )
        assert mock_explain.call_count == 1
        assert result["refreshed"] == 1
        assert result["skipped"] == 0


def test_refresh_handles_store_exceptions():
    """Should gracefully skip metrics when store raises exceptions."""
    mock_registry = [
        {"fqn": "a.b.revenue", "display_name": "Revenue"},
        {"fqn": "a.b.signups", "display_name": "Signups"},
    ]
    mock_store = MagicMock()
    mock_store.list_metric_runs.side_effect = Exception("Query timeout")

    with patch("dqt.insights.scheduler.explain_movement") as mock_explain:
        result = refresh_all_narratives(
            metric_catalog=mock_registry,
            store=mock_store,
            window=timedelta(days=1),
            min_change_threshold=0.02,
        )
        mock_explain.assert_not_called()
        assert result["refreshed"] == 0
        assert result["skipped"] == 2


def test_refresh_requires_at_least_two_runs():
    """Should skip metrics with fewer than 2 runs."""
    mock_registry = [{"fqn": "a.b.revenue", "display_name": "Revenue"}]
    mock_store = MagicMock()
    mock_store.list_metric_runs.return_value = [MagicMock(value=100.0)]

    with patch("dqt.insights.scheduler.explain_movement") as mock_explain:
        result = refresh_all_narratives(
            metric_catalog=mock_registry,
            store=mock_store,
            window=timedelta(days=1),
            min_change_threshold=0.02,
        )
        mock_explain.assert_not_called()
        assert result["refreshed"] == 0
        assert result["skipped"] == 1


def test_refresh_skips_zero_baseline():
    """Should skip metrics with zero baseline value to avoid division by zero."""
    mock_registry = [{"fqn": "a.b.revenue", "display_name": "Revenue"}]
    mock_store = MagicMock()
    run_before = MagicMock()
    run_before.value = 0.0
    run_after = MagicMock()
    run_after.value = 100.0
    mock_store.list_metric_runs.return_value = [run_before, run_after]

    with patch("dqt.insights.scheduler.explain_movement") as mock_explain:
        result = refresh_all_narratives(
            metric_catalog=mock_registry,
            store=mock_store,
            window=timedelta(days=1),
            min_change_threshold=0.02,
        )
        mock_explain.assert_not_called()
        assert result["refreshed"] == 0
        assert result["skipped"] == 1


def test_refresh_respects_use_llm_parameter():
    """Should pass use_llm parameter to explain_movement."""
    mock_registry = [{"fqn": "a.b.revenue", "display_name": "Revenue"}]
    mock_store = MagicMock()
    run_before = MagicMock()
    run_before.value = 100.0
    run_after = MagicMock()
    run_after.value = 50.0
    mock_store.list_metric_runs.return_value = [run_before, run_after]

    with patch("dqt.insights.scheduler.explain_movement") as mock_explain:
        mock_explain.return_value = MagicMock()
        refresh_all_narratives(
            metric_catalog=mock_registry,
            store=mock_store,
            window=timedelta(days=1),
            min_change_threshold=0.02,
            use_llm=False,
        )
        # Check that use_llm=False was passed
        call_kwargs = mock_explain.call_args[1]
        assert call_kwargs["use_llm"] is False

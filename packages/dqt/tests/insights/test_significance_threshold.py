import pytest
from datetime import datetime, timedelta, timezone

from dqt.store._protocol import MetricRun
from dqt.insights.threshold import compute_threshold, _DEFAULT_THRESHOLD


def _runs(values: list[float]) -> list[MetricRun]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        MetricRun(metric_fqn="test", run_at=base + timedelta(days=i), value=v, verdict="pass")
        for i, v in enumerate(values)
    ]


def test_insufficient_history_returns_default():
    assert compute_threshold(_runs([1.0, 0.95, 1.02, 0.98])) == _DEFAULT_THRESHOLD


def test_stable_metric_has_low_threshold():
    # Oscillates +-1% -- threshold should be well below 5%
    values = [1.0 + (i % 2) * 0.01 for i in range(30)]
    assert compute_threshold(_runs(values)) < 0.05


def test_volatile_metric_has_higher_threshold():
    # Oscillates +-20% -- threshold should exceed 10%
    values = [1.0 + (i % 2) * 0.20 for i in range(30)]
    assert compute_threshold(_runs(values)) > 0.10


def test_threshold_never_below_one_percent():
    # Perfectly flat metric -- std=0, threshold = mean+0 but clamped to 0.01
    assert compute_threshold(_runs([1.0] * 30)) >= 0.01


def test_higher_sigma_gives_higher_threshold():
    values = [1.0 + (i % 2) * 0.05 for i in range(30)]
    t1 = compute_threshold(_runs(values), sigma=1.0)
    t3 = compute_threshold(_runs(values), sigma=3.0)
    assert t3 > t1


def test_zero_previous_value_is_skipped():
    # If a run has value 0, the next day-over-day change is skipped (div by zero guard)
    values = [0.0, 1.0] + [1.0 + (i % 2) * 0.02 for i in range(28)]
    threshold = compute_threshold(_runs(values))
    assert threshold >= 0.01

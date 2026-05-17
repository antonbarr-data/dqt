from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from dqt.store.memory import MemoryStore
from dqt.store._protocol import MetricRun
from dqt.subscriptions.models import Subscription
from dqt.subscriptions.store import SubscriptionStore
from dqt.insights.trigger import check_thresholds


def _seed(store: MemoryStore, fqn: str, values: list[tuple[int, float]]) -> None:
    """Seed metric runs relative to now. days_ago=0 means today."""
    now = datetime.now(timezone.utc)
    for days_ago, val in values:
        store.save_metric_run(
            MetricRun(metric_fqn=fqn, run_at=now - timedelta(days=days_ago), value=val, verdict="pass")
        )


def _slack_mock() -> MagicMock:
    m = MagicMock()
    type(m).__name__ = "SlackNotifier"
    m.send_blocks = MagicMock(return_value=True)
    return m


def _email_mock() -> MagicMock:
    m = MagicMock()
    type(m).__name__ = "EmailNotifier"
    m.send = MagicMock(return_value=True)
    return m


def test_no_subscribers_skips_metric():
    store = MemoryStore()
    _seed(store, "m1", [(7, 1.0), (0, 0.50)])
    result = check_thresholds(
        [{"fqn": "m1", "display_name": "M1"}], store, SubscriptionStore(), []
    )
    assert result["triggered"] == 0
    assert result["skipped"] == 1


def test_large_drop_fires_slack_notification():
    store = MemoryStore()
    _seed(store, "m1", [(7, 1.0), (6, 1.0), (5, 1.0), (4, 1.0), (3, 1.0), (2, 1.0), (1, 1.0), (0, 0.50)])
    sub_store = SubscriptionStore()
    sub = Subscription(
        user_id="alice@example.com",
        metric_fqns=["m1"],
        cadence="on_threshold",
        delivery_channels=["slack"],
    )
    sub_store.save(sub)
    slack = _slack_mock()
    result = check_thresholds([{"fqn": "m1", "display_name": "M1"}], store, sub_store, [slack])
    assert result["triggered"] == 1
    assert slack.send_blocks.called


def test_small_change_below_subscriber_threshold_does_not_notify():
    store = MemoryStore()
    _seed(store, "m1", [(7, 1.0), (6, 1.0), (5, 1.0), (4, 1.0), (3, 1.0), (2, 1.0), (1, 1.0), (0, 0.97)])
    sub_store = SubscriptionStore()
    sub = Subscription(
        user_id="bob@example.com",
        metric_fqns=["m1"],
        cadence="on_threshold",
        delivery_channels=["email"],
        significance_threshold=0.10,  # 10% -- change is only 3%
    )
    sub_store.save(sub)
    email = _email_mock()
    result = check_thresholds([{"fqn": "m1", "display_name": "M1"}], store, sub_store, [email])
    assert result["triggered"] == 0
    assert not email.send.called


def test_per_subscriber_threshold_override():
    store = MemoryStore()
    _seed(store, "m1", [(7, 1.0), (6, 1.0), (5, 1.0), (4, 1.0), (3, 1.0), (2, 1.0), (1, 1.0), (0, 0.96)])
    sub_store = SubscriptionStore()
    # Alice triggers at 3%, Bob does not trigger at 10%
    sub_store.save(Subscription(user_id="alice@example.com", metric_fqns=["m1"], cadence="on_threshold", delivery_channels=["slack"], significance_threshold=0.03))
    sub_store.save(Subscription(user_id="bob@example.com", metric_fqns=["m1"], cadence="on_threshold", delivery_channels=["slack"], significance_threshold=0.10))

    call_count = [0]
    slack = _slack_mock()
    def counting(*a, **kw):
        call_count[0] += 1
        return True
    slack.send_blocks = counting

    check_thresholds([{"fqn": "m1", "display_name": "M1"}], store, sub_store, [slack])
    assert call_count[0] == 1


def test_email_channel_routes_to_email_notifier():
    store = MemoryStore()
    _seed(store, "m1", [(7, 1.0), (6, 1.0), (5, 1.0), (4, 1.0), (3, 1.0), (2, 1.0), (1, 1.0), (0, 0.50)])
    sub_store = SubscriptionStore()
    sub_store.save(Subscription(user_id="carol@example.com", metric_fqns=["m1"], cadence="on_threshold", delivery_channels=["email"]))
    email = _email_mock()
    slack = _slack_mock()
    check_thresholds([{"fqn": "m1", "display_name": "M1"}], store, sub_store, [slack, email])
    assert email.send.called
    assert not slack.send_blocks.called

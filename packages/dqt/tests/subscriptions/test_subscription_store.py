import pytest
from dqt.subscriptions.models import Subscription
from dqt.subscriptions.store import SubscriptionStore


def test_save_and_retrieve():
    store = SubscriptionStore()
    sub = Subscription(
        user_id="alice",
        metric_fqns=["src.db.orders.quality"],
        cadence="daily",
        delivery_channels=["email"],
    )
    store.save(sub)
    retrieved = store.get(sub.id)
    assert retrieved is not None
    assert retrieved.user_id == "alice"
    assert "src.db.orders.quality" in retrieved.metric_fqns


def test_list_for_user_filters_by_user():
    store = SubscriptionStore()
    sub1 = Subscription(user_id="alice", metric_fqns=["m1"], cadence="daily", delivery_channels=["email"])
    sub2 = Subscription(user_id="bob", metric_fqns=["m2"], cadence="weekly", delivery_channels=["slack"])
    store.save(sub1)
    store.save(sub2)
    alice_subs = store.list_for_user("alice")
    assert len(alice_subs) == 1
    assert alice_subs[0].user_id == "alice"


def test_list_for_metric():
    store = SubscriptionStore()
    sub = Subscription(
        user_id="alice",
        metric_fqns=["orders.q", "sessions.q"],
        cadence="daily",
        delivery_channels=["email"],
    )
    store.save(sub)
    result = store.list_for_metric("orders.q")
    assert len(result) == 1
    assert result[0].user_id == "alice"


def test_delete_returns_true_when_found():
    store = SubscriptionStore()
    sub = Subscription(user_id="alice", metric_fqns=["m1"], cadence="daily", delivery_channels=["email"])
    store.save(sub)
    assert store.delete(sub.id) is True
    assert store.get(sub.id) is None


def test_delete_returns_false_when_not_found():
    store = SubscriptionStore()
    sub = Subscription(user_id="alice", metric_fqns=["m1"], cadence="daily", delivery_channels=["email"])
    store.save(sub)
    store.delete(sub.id)
    assert store.delete(sub.id) is False


def test_update_replaces_subscription():
    store = SubscriptionStore()
    sub = Subscription(user_id="alice", metric_fqns=["m1"], cadence="daily", delivery_channels=["email"])
    store.save(sub)
    sub.cadence = "weekly"
    store.update(sub)
    assert store.get(sub.id).cadence == "weekly"

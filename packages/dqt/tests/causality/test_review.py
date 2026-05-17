# packages/dqt/tests/causality/test_review.py
from __future__ import annotations
import pytest
from dqt.causality.review import CausalReviewEdge, ReviewStore


def _edge(cause: str = "views", effect: str = "revenue", status: str = "pending") -> CausalReviewEdge:
    return CausalReviewEdge(
        id=f"{cause}->{effect}",
        cause=cause,
        effect=effect,
        p_value=0.02,
        evidence_strength="moderate",
        status=status,
    )


def test_store_add_and_list():
    store = ReviewStore()
    store.add(_edge("a", "b"))
    store.add(_edge("c", "d"))
    pending = store.list_pending()
    assert len(pending) == 2


def test_store_accept():
    store = ReviewStore()
    e = _edge()
    store.add(e)
    store.review(e.id, decision="accept", reviewer="alice", notes="looks good")
    pending = store.list_pending()
    assert len(pending) == 0
    accepted = store.list_by_status("accepted")
    assert len(accepted) == 1
    assert accepted[0].reviewer == "alice"
    assert accepted[0].notes == "looks good"


def test_store_reject():
    store = ReviewStore()
    e = _edge()
    store.add(e)
    store.review(e.id, decision="reject", reviewer="bob", notes="confounder")
    assert len(store.list_by_status("rejected")) == 1


def test_store_unknown_id_raises():
    store = ReviewStore()
    with pytest.raises(KeyError):
        store.review("nonexistent", decision="accept", reviewer="x")


def test_stats_empty():
    store = ReviewStore()
    stats = store.stats()
    assert stats["total"] == 0
    assert stats["pending"] == 0
    assert stats["accepted"] == 0
    assert stats["rejected"] == 0


def test_stats_after_reviews():
    store = ReviewStore()
    store.add(_edge("a", "b"))
    store.add(_edge("c", "d"))
    store.add(_edge("e", "f"))
    store.review("a->b", decision="accept", reviewer="x")
    store.review("c->d", decision="reject", reviewer="x")
    stats = store.stats()
    assert stats["total"] == 3
    assert stats["pending"] == 1
    assert stats["accepted"] == 1
    assert stats["rejected"] == 1
    assert round(stats["accept_rate"], 2) == 0.5

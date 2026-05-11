from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.mark.unit
def test_save_and_list_causal_reviews():
    """ResultsStore can persist and retrieve CausalEdgeReview records."""
    from dqt.store.memory import MemoryStore
    from dqt.store._protocol import CausalEdgeReview

    store = MemoryStore()
    edge_id = uuid4()
    review = CausalEdgeReview(
        edge_id=edge_id,
        cause="revenue",
        effect="bookings",
        decision="accept",
        reviewer="analyst@example.com",
        reviewed_at=datetime.now(timezone.utc),
        reason="Confirmed by domain knowledge",
    )
    store.save_causal_review(review)
    reviews = store.list_causal_reviews(edge_id=edge_id)
    assert len(reviews) == 1
    assert reviews[0].decision == "accept"


@pytest.mark.unit
def test_causal_edge_precision():
    """Precision report counts accept vs reject for an edge."""
    from dqt.store.memory import MemoryStore
    from dqt.store._protocol import CausalEdgeReview

    store = MemoryStore()
    edge_id = uuid4()
    for decision in ["accept", "accept", "reject", "defer"]:
        store.save_causal_review(CausalEdgeReview(
            edge_id=edge_id, cause="x", effect="y", decision=decision,
            reviewer="r", reviewed_at=datetime.now(timezone.utc),
        ))
    precision = store.causal_edge_precision(edge_id=edge_id)
    # 2 accept / 3 decided (accept+reject) = 0.667; defer is excluded
    assert abs(precision - 2 / 3) < 0.01


@pytest.mark.unit
def test_causal_edge_precision_no_decisions():
    """Empty reviews returns nan."""
    import math
    from dqt.store.memory import MemoryStore

    store = MemoryStore()
    edge_id = uuid4()
    precision = store.causal_edge_precision(edge_id=edge_id)
    assert math.isnan(precision)


@pytest.mark.unit
def test_list_causal_reviews_filters_by_edge_id():
    """list_causal_reviews returns only reviews for the requested edge."""
    from dqt.store.memory import MemoryStore
    from dqt.store._protocol import CausalEdgeReview

    store = MemoryStore()
    edge_a, edge_b = uuid4(), uuid4()
    store.save_causal_review(CausalEdgeReview(
        edge_id=edge_a, cause="x", effect="y", decision="accept",
        reviewer="r", reviewed_at=datetime.now(timezone.utc),
    ))
    store.save_causal_review(CausalEdgeReview(
        edge_id=edge_b, cause="a", effect="b", decision="reject",
        reviewer="r", reviewed_at=datetime.now(timezone.utc),
    ))
    assert len(store.list_causal_reviews(edge_id=edge_a)) == 1
    assert len(store.list_causal_reviews(edge_id=edge_b)) == 1

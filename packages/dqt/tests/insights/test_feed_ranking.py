from datetime import timedelta
from dqt.insights.feed import FeedItem, rank

def _make_item(fqn: str, magnitude: float, significance: float,
               executive: bool = False, novelty: float = 1.0, engagement: float = 0.0) -> FeedItem:
    return FeedItem(
        metric_fqn=fqn,
        display_name=fqn.split(".")[-1],
        observed_change=magnitude,
        significance=significance,
        executive_tier=executive,
        novelty=novelty,
        engagement=engagement,
        summary_paragraph="Test narrative.",
        primary_channel="mixed",
        estimated_data_contribution=(0.1, 0.3),
        estimated_business_contribution=(0.2, 0.5),
        evidence_chips=[],
    )

def test_rank_sorts_by_score():
    items = [
        _make_item("a.b.c.low", magnitude=0.02, significance=0.3),
        _make_item("a.b.c.high", magnitude=0.18, significance=0.95, executive=True),
        _make_item("a.b.c.mid", magnitude=0.08, significance=0.6),
    ]
    ranked = rank(items, window=timedelta(hours=24), limit=10)
    assert ranked[0].metric_fqn == "a.b.c.high"
    assert ranked[-1].metric_fqn == "a.b.c.low"

def test_rank_applies_limit():
    items = [_make_item(f"m.m.m.{i}", magnitude=0.1 + i * 0.01, significance=0.9)
             for i in range(25)]
    ranked = rank(items, window=timedelta(hours=24), limit=20)
    assert len(ranked) == 20

def test_rank_novelty_decay():
    fresh = _make_item("a.b.c.fresh", magnitude=0.10, significance=0.8, novelty=1.0)
    stale = _make_item("a.b.c.stale", magnitude=0.10, significance=0.8, novelty=0.1)
    ranked = rank([stale, fresh], window=timedelta(hours=24), limit=10)
    assert ranked[0].metric_fqn == "a.b.c.fresh"

def test_rank_empty():
    assert rank([], window=timedelta(hours=24), limit=20) == []

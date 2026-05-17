from datetime import datetime, timedelta, timezone

from dqt.store.memory import MemoryStore
from dqt.store._protocol import MetricRun
from dqt.insights.digest import generate_daily


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed(store: MemoryStore, fqn: str, values: list[tuple[int, float]]) -> None:
    for days_ago, val in values:
        store.save_metric_run(
            MetricRun(metric_fqn=fqn, run_at=_now() - timedelta(days=days_ago), value=val, verdict="pass")
        )


def test_flat_metric_goes_to_no_significant_change():
    store = MemoryStore()
    _seed(store, "m1", [(8, 1.0), (7, 1.005), (6, 0.998), (5, 1.002), (4, 1.001), (3, 0.999), (2, 1.003), (1, 1.001), (0, 1.000)])
    catalog = [{"fqn": "m1", "display_name": "Orders Quality"}]
    digest = generate_daily(catalog, store, significant_threshold=0.02)
    assert len(digest.no_significant_change) == 1
    assert len(digest.data_issues) + len(digest.real_shifts) == 0


def test_significant_drop_is_classified():
    store = MemoryStore()
    _seed(store, "revenue", [(8, 100.0), (7, 100.0), (6, 100.0), (5, 100.0), (4, 100.0), (3, 100.0), (2, 100.0), (1, 100.0), (0, 82.0)])
    catalog = [{"fqn": "revenue", "display_name": "Revenue"}]
    digest = generate_daily(catalog, store, significant_threshold=0.02)
    total = len(digest.data_issues) + len(digest.real_shifts)
    assert total == 1


def test_to_plain_text_contains_metric_name():
    store = MemoryStore()
    _seed(store, "m1", [(8, 1.0), (0, 0.75)])
    catalog = [{"fqn": "m1", "display_name": "Orders Quality"}]
    digest = generate_daily(catalog, store)
    text = digest.to_plain_text()
    assert "Daily Digest" in text
    assert "Orders Quality" in text


def test_to_slack_blocks_has_header():
    store = MemoryStore()
    _seed(store, "m1", [(8, 1.0), (0, 0.75)])
    catalog = [{"fqn": "m1", "display_name": "Orders Quality"}]
    blocks = generate_daily(catalog, store).to_slack_blocks()
    assert isinstance(blocks, list)
    assert any(b.get("type") == "header" for b in blocks)


def test_to_html_is_valid_html():
    store = MemoryStore()
    _seed(store, "m1", [(8, 1.0), (0, 0.75)])
    catalog = [{"fqn": "m1", "display_name": "Orders Quality"}]
    html = generate_daily(catalog, store).to_html()
    assert "<!DOCTYPE html>" in html
    assert "Daily Digest" in html
    assert "Orders Quality" in html


def test_metric_with_insufficient_runs_is_skipped():
    store = MemoryStore()
    _seed(store, "m1", [(0, 1.0)])  # only 1 run -- skip
    catalog = [{"fqn": "m1", "display_name": "M1"}]
    digest = generate_daily(catalog, store)
    assert len(digest.data_issues) + len(digest.real_shifts) + len(digest.no_significant_change) == 0

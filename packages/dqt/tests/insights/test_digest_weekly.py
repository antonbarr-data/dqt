from datetime import datetime, timedelta, timezone

from dqt.store.memory import MemoryStore
from dqt.store._protocol import MetricRun
from dqt.insights.digest import generate_weekly


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed(store: MemoryStore, fqn: str, values: list[tuple[int, float]]) -> None:
    for days_ago, val in values:
        store.save_metric_run(
            MetricRun(metric_fqn=fqn, run_at=_now() - timedelta(days=days_ago), value=val, verdict="pass")
        )


def test_weekly_groups_flat_and_shifted_metrics():
    store = MemoryStore()
    _seed(store, "m1", [(14, 1.0), (7, 1.005), (0, 1.003)])  # flat
    _seed(store, "m2", [(14, 1.0), (7, 1.0), (0, 0.75)])       # big drop
    catalog = [{"fqn": "m1", "display_name": "M1"}, {"fqn": "m2", "display_name": "M2"}]
    digest = generate_weekly(catalog, store, significant_threshold=0.02)
    assert len(digest.no_significant_change) == 1
    assert len(digest.data_issues) + len(digest.real_shifts) == 1


def test_weekly_plain_text_header():
    digest = generate_weekly([], MemoryStore())
    assert "Weekly Digest" in digest.to_plain_text()


def test_weekly_html_contains_section_heading():
    store = MemoryStore()
    _seed(store, "m1", [(14, 1.0), (0, 0.75)])
    catalog = [{"fqn": "m1", "display_name": "M1"}]
    html = generate_weekly(catalog, store).to_html()
    assert "Real Shifts" in html or "Data Issues" in html


def test_weekly_slack_blocks_list():
    digest = generate_weekly([], MemoryStore())
    blocks = digest.to_slack_blocks()
    assert isinstance(blocks, list)

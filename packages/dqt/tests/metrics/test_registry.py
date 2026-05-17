from dqt.metrics import Metric, MetricRegistry


def _make_registry(metrics: list[Metric]) -> MetricRegistry:
    return MetricRegistry(metrics)


def _metric(**kw) -> Metric:
    defaults = dict(
        display_name="Test Metric", kind="count", dataset="ds",
        description="", owners=[], tags=[],
    )
    return Metric(**{**defaults, **kw})


def test_metric_has_required_fields():
    m = Metric(
        fqn="gigler.public.gigler_transactions.null_fraction",
        display_name="Null fraction -- gigler_transactions",
        kind="ratio",
        dataset="gigler_transactions",
        description="Fraction of NULL values.",
        owners=[],
        tags=[],
    )
    assert m.fqn
    assert m.display_name
    assert m.kind in ("ratio", "count", "sum", "model")


def test_registry_get():
    m = _metric(fqn="a.b.c.d")
    reg = _make_registry([m])
    assert reg.get("a.b.c.d") is m


def test_registry_get_missing_returns_none():
    reg = _make_registry([])
    assert reg.get("nonexistent") is None


def test_registry_search_by_display_name():
    m1 = _metric(fqn="a", display_name="Revenue total", dataset="orders")
    m2 = _metric(fqn="b", display_name="Churn rate", dataset="users")
    reg = _make_registry([m1, m2])
    results = reg.search("revenue")
    assert any(r.fqn == "a" for r in results)
    assert not any(r.fqn == "b" for r in results)


def test_registry_search_case_insensitive():
    m = _metric(fqn="a", display_name="Revenue Total")
    reg = _make_registry([m])
    assert reg.search("REVENUE")


def test_registry_list_all():
    metrics = [_metric(fqn=f"m{i}") for i in range(5)]
    reg = _make_registry(metrics)
    assert len(reg.list()) == 5


def test_registry_list_filter_by_tag():
    m1 = _metric(fqn="a", tags=["finance"])
    m2 = _metric(fqn="b", tags=["marketing"])
    reg = _make_registry([m1, m2])
    assert [r.fqn for r in reg.list(tags=["finance"])] == ["a"]


def test_registry_list_filter_by_owner():
    m1 = _metric(fqn="a", owners=["alice"])
    m2 = _metric(fqn="b", owners=["bob"])
    reg = _make_registry([m1, m2])
    assert [r.fqn for r in reg.list(owner="alice")] == ["a"]


def test_registry_reload():
    m1 = _metric(fqn="a")
    m2 = _metric(fqn="b")
    reg = _make_registry([m1])
    assert reg.get("b") is None
    reg.reload([m1, m2])
    assert reg.get("b") is m2


def test_empty_registry_list_returns_empty():
    reg = _make_registry([])
    assert reg.list() == []

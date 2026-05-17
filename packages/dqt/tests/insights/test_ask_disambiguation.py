from dqt.insights.ask import resolve, AskResult, DisambiguationResult

_AMBIGUOUS_METRICS = [
    {"fqn": "acme.a.revenue_usd", "display_name": "Revenue USD"},
    {"fqn": "acme.b.revenue_eur", "display_name": "Revenue EUR"},
]

def test_ambiguous_returns_disambiguation():
    result = resolve("Why is revenue down?", metric_catalog=_AMBIGUOUS_METRICS)
    assert isinstance(result, DisambiguationResult)
    assert len(result.options) >= 2

def test_no_match_returns_disambiguation():
    result = resolve("Why is churn so high?", metric_catalog=[])
    assert isinstance(result, DisambiguationResult)
    assert result.options == []

def test_high_confidence_does_not_disambiguate():
    metrics = [{"fqn": "acme.a.signups", "display_name": "New Signups"}]
    result = resolve("Why did new signups drop this week?", metric_catalog=metrics)
    assert isinstance(result, AskResult)

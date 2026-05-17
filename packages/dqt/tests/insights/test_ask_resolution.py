from dqt.insights.ask import resolve, AskResult, DisambiguationResult

_METRICS = [
    {"fqn": "acme.sales.fct_orders.revenue", "display_name": "Revenue"},
    {"fqn": "acme.sales.fct_orders.signups", "display_name": "New Signups"},
    {"fqn": "acme.sales.fct_sessions.cancellations", "display_name": "Cancellation Rate"},
]

def test_resolve_why_question():
    result = resolve("Why is revenue down this week?", metric_catalog=_METRICS)
    assert isinstance(result, AskResult)
    assert result.intent == "why"
    assert "revenue" in result.metric_fqn.lower()
    assert result.window_days == 7

def test_resolve_data_issue_question():
    result = resolve("Is the drop in signups a data issue?", metric_catalog=_METRICS)
    assert isinstance(result, AskResult)
    assert result.intent == "why"
    assert "signup" in result.metric_fqn.lower()

def test_resolve_30_day_window():
    result = resolve("What's driving the spike in cancellations last 30 days?", metric_catalog=_METRICS)
    assert isinstance(result, AskResult)
    assert result.window_days == 30
    assert "cancellation" in result.metric_fqn.lower()

def test_resolve_list_intent():
    result = resolve("Show me which metrics moved significantly yesterday", metric_catalog=_METRICS)
    assert isinstance(result, AskResult)
    assert result.intent == "list"
    assert result.window_days == 1

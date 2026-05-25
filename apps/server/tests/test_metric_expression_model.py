import pytest
from dqt_server.models.core import MetricDefinition, MetricRun


def test_metric_definition_has_expression_fields():
    m = MetricDefinition(
        fqn="test.default.orders.take_rate",
        display_name="Take Rate",
        kind="ratio",
        dataset="orders",
        expr_type="ratio",
        expr_sql="(SUM(fee_usd)) / NULLIF((SUM(amount_usd)), 0)",
        numerator_sql="SUM(fee_usd)",
        denominator_sql="SUM(amount_usd)",
        filter_sql="status = 'completed'",
        time_column="date",
    )
    assert m.expr_type == "ratio"
    assert "NULLIF" in m.expr_sql
    assert m.time_column == "date"


def test_metric_run_model():
    r = MetricRun(fqn="test.default.orders.take_rate", value=0.0342)
    assert r.fqn == "test.default.orders.take_rate"
    assert r.value == pytest.approx(0.0342)

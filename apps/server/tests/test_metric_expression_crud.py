import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from dqt_server.main import app


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.mark.asyncio
async def test_create_metric_with_expression():
    dataset = f"gigler_expr_create_{_uid()}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/metrics", json={
            "display_name": f"Take Rate {_uid()}",
            "kind": "ratio",
            "dataset": dataset,
            "expr_type": "ratio",
            "expr_sql": "(SUM(platform_fee_usd)) / NULLIF((SUM(amount_usd)), 0)",
            "numerator_sql": "SUM(platform_fee_usd)",
            "denominator_sql": "SUM(amount_usd)",
            "filter_sql": "status = 'completed'",
            "time_column": "date",
        })
    assert resp.status_code == 201
    assert "fqn" in resp.json()


@pytest.mark.asyncio
async def test_get_metric_returns_expression_fields():
    dataset = f"gigler_expr_fields_{_uid()}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cr = await client.post("/api/v1/metrics", json={
            "display_name": f"Expr Fields {_uid()}",
            "kind": "ratio",
            "dataset": dataset,
            "expr_type": "ratio",
            "expr_sql": "(SUM(fee)) / NULLIF((SUM(total)), 0)",
            "numerator_sql": "SUM(fee)",
            "denominator_sql": "SUM(total)",
            "filter_sql": "active = true",
            "time_column": "created_at",
        })
        assert cr.status_code == 201
        fqn = cr.json()["fqn"]

        dr = await client.get(f"/api/v1/metrics/{fqn}")
    assert dr.status_code == 200
    body = dr.json()
    assert body["expr_type"] == "ratio"
    assert "NULLIF" in body["expr_sql"]
    assert body["numerator_sql"] == "SUM(fee)"
    assert body["filter_sql"] == "active = true"
    assert body["time_column"] == "created_at"


@pytest.mark.asyncio
async def test_patch_metric_expression():
    dataset = f"gigler_patch_expr_{_uid()}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cr = await client.post("/api/v1/metrics", json={
            "display_name": f"Patch Expr {_uid()}",
            "kind": "simple",
            "dataset": dataset,
        })
        assert cr.status_code == 201
        fqn = cr.json()["fqn"]

        pr = await client.patch(f"/api/v1/metrics/{fqn}", json={
            "expr_type": "simple",
            "expr_sql": "COUNT(*)",
        })
        assert pr.status_code == 200

        dr = await client.get(f"/api/v1/metrics/{fqn}")
    assert dr.status_code == 200
    assert dr.json()["expr_sql"] == "COUNT(*)"
    assert dr.json()["expr_type"] == "simple"

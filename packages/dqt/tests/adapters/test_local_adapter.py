import pathlib

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "id": range(200),
        "amount": rng.normal(100.0, 15.0, 200),
        "status": ["active" if i % 2 == 0 else None for i in range(200)],
    })


@pytest.fixture(scope="module")
def csv_file(tmp_path_factory, sample_df) -> pathlib.Path:
    p = tmp_path_factory.mktemp("files") / "orders.csv"
    sample_df.to_csv(p, index=False)
    return p


@pytest.fixture(scope="module")
def parquet_file(tmp_path_factory, sample_df) -> pathlib.Path:
    p = tmp_path_factory.mktemp("files") / "orders.parquet"
    sample_df.to_parquet(p, index=False)
    return p


@pytest.fixture(scope="module")
def json_file(tmp_path_factory, sample_df) -> pathlib.Path:
    p = tmp_path_factory.mktemp("files") / "orders.json"
    sample_df.to_json(p, orient="records")
    return p


@pytest.fixture(scope="module")
def jsonl_file(tmp_path_factory, sample_df) -> pathlib.Path:
    p = tmp_path_factory.mktemp("files") / "orders.jsonl"
    sample_df.to_json(p, orient="records", lines=True)
    return p


def test_csv_health_check_passes(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(csv_file)
    result = adapter.health_check()
    assert result.passed, [s for s in result.steps if s.status not in ("pass", "skip")]


def test_health_check_fails_missing_file(tmp_path):
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter.__new__(LocalFileAdapter)
    adapter._path = tmp_path / "ghost.csv"
    adapter._suffix = ".csv"
    adapter._table_name = "ghost"
    result = adapter.health_check()
    assert not result.passed
    assert result.steps[0].name == "file_exists"
    assert result.steps[0].status == "fail"


def test_list_schemas(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    assert LocalFileAdapter(csv_file).list_schemas() == ["default"]


def test_list_tables_returns_stem(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    assert LocalFileAdapter(csv_file).list_tables("default") == ["orders"]


def test_describe_columns_csv(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    cols = LocalFileAdapter(csv_file).describe_columns("default", "orders")
    names = [c.name for c in cols]
    assert "id" in names and "amount" in names and "status" in names
    status_col = next(c for c in cols if c.name == "status")
    assert status_col.nullable is True


def test_sample_csv_limit(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    df = LocalFileAdapter(csv_file).sample("default", "orders", n=50)
    assert len(df) == 50


def test_sample_csv_full_when_small(csv_file, sample_df):
    from dqt.adapters.local import LocalFileAdapter
    df = LocalFileAdapter(csv_file).sample("default", "orders", n=100_000)
    assert len(df) == len(sample_df)


def test_aggregate_csv(csv_file):
    from dqt.adapters._protocol import AggExpr
    from dqt.adapters.local import LocalFileAdapter
    result = LocalFileAdapter(csv_file).aggregate("default", "orders", [
        AggExpr(name="total", sql="COUNT(*)"),
        AggExpr(name="null_status", sql="SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END)"),
    ])
    assert result["total"] == 200
    assert result["null_status"] == 100


def test_parquet_roundtrip(parquet_file):
    from dqt.adapters._protocol import AggExpr
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(parquet_file)
    assert adapter.health_check().passed
    result = adapter.aggregate("default", "orders", [AggExpr(name="n", sql="COUNT(*)")])
    assert result["n"] == 200


def test_json_roundtrip(json_file):
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(json_file)
    assert adapter.health_check().passed
    df = adapter.sample("default", "orders", n=10)
    assert len(df) == 10


def test_jsonl_roundtrip(jsonl_file):
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(jsonl_file)
    assert adapter.health_check().passed
    df = adapter.sample("default", "orders")
    assert len(df) == 200


def test_unsupported_format_raises(tmp_path):
    from dqt.adapters.local import LocalFileAdapter
    with pytest.raises(ValueError, match="Unsupported format"):
        LocalFileAdapter(tmp_path / "data.xyz")


def test_implements_warehouse_adapter_protocol(csv_file):
    from dqt.adapters._protocol import WarehouseAdapter
    from dqt.adapters.local import LocalFileAdapter
    assert isinstance(LocalFileAdapter(csv_file), WarehouseAdapter)

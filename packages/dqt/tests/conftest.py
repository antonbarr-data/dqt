import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="session")
def normal_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({"value": rng.normal(loc=10.0, scale=2.0, size=1_000)})


@pytest.fixture(scope="session")
def shifted_df() -> pd.DataFrame:
    rng = np.random.default_rng(99)
    return pd.DataFrame({"value": rng.normal(loc=15.0, scale=2.0, size=1_000)})


@pytest.fixture(scope="session")
def timeseries_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 365
    trend = np.linspace(100.0, 110.0, n)
    seasonal = 5.0 * np.sin(2 * np.pi * np.arange(n) / 7)
    noise = rng.normal(0, 1.0, n)
    return pd.DataFrame({"value": trend + seasonal + noise})


@pytest.fixture(scope="session")
def agg_ref_df() -> pd.DataFrame:
    return pd.DataFrame([{"null_count": 5, "total_count": 1_000}])


@pytest.fixture(scope="session")
def agg_curr_df() -> pd.DataFrame:
    return pd.DataFrame([{"null_count": 80, "total_count": 1_000}])


@pytest.fixture
def fake_adapter():
    """Adapter that returns a tiny 10-row DataFrame for power-warning tests."""
    import numpy as np
    from dqt.adapters._protocol import HealthCheckResult

    class _TinyAdapter:
        def sample(self, schema, table, n=100_000, **kwargs):
            rng = np.random.default_rng(0)
            return pd.DataFrame({"val": rng.normal(0, 1, 10)})
        def aggregate(self, schema, table, exprs):
            return {e.name: 0.0 for e in exprs}
        def list_schemas(self): return ["s"]
        def list_tables(self, schema): return ["t"]
        def describe_columns(self, schema, table): return []
        def health_check(self): return HealthCheckResult(steps=[])

    return _TinyAdapter()

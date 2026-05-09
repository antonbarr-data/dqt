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

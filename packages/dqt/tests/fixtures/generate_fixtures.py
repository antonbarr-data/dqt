"""Run once to regenerate fixture CSVs: python generate_fixtures.py"""
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent
RNG = np.random.default_rng(0)

# ---------------------------------------------------------------------------
# orders_dirty.csv
# 500 rows, 15% injected outliers in amount_usd (column index 4)
# ---------------------------------------------------------------------------
n = 500
n_dirty = 75  # 15%
order_id = np.arange(1, n + 1)
quantity = RNG.integers(1, 20, size=n)
discount_pct = RNG.uniform(0, 0.3, size=n)
is_refund = RNG.integers(0, 2, size=n)
amount_usd = np.concatenate([
    np.exp(RNG.normal(6.0, 0.5, n - n_dirty)),   # normal orders ~$400
    np.exp(RNG.normal(9.5, 0.3, n_dirty)),         # dirty orders ~$13k (10x normal)
])
RNG.shuffle(amount_usd)
dates = pd.date_range("2024-01-01", periods=n, freq="h")
customer_id = RNG.integers(1000, 9999, size=n)

df_orders = pd.DataFrame({
    "order_id": order_id,
    "quantity": quantity,
    "discount_pct": discount_pct.round(4),
    "is_refund": is_refund,
    "amount_usd": amount_usd.round(2),
    "created_at": dates.strftime("%Y-%m-%dT%H:%M:%S"),
    "customer_id": customer_id,
})
df_orders.to_csv(OUT / "orders_dirty.csv", index=False)
print(f"orders_dirty.csv: {len(df_orders)} rows, amount_usd at col index 4")

# ---------------------------------------------------------------------------
# hourly_causal.csv
# 500 rows, x->y (lag 1), y->z (lag 1)
# ---------------------------------------------------------------------------
n = 500
x = RNG.normal(0, 1, n)
y = np.zeros(n)
z = np.zeros(n)
for i in range(1, n):
    y[i] = 0.8 * x[i - 1] + RNG.normal(0, 0.2)
    z[i] = 0.8 * y[i - 1] + RNG.normal(0, 0.2)

df_causal = pd.DataFrame({"x": x, "y": y, "z": z})
df_causal.to_csv(OUT / "hourly_causal.csv", index=False)
print(f"hourly_causal.csv: {len(df_causal)} rows, x->y->z causal chain")

# ---------------------------------------------------------------------------
# daily_metrics_dirty.csv
# 200 rows, drift starts at row 100 (value shifts from ~100 to ~130)
# ---------------------------------------------------------------------------
n = 200
n_ref = 100
stable_part = RNG.normal(100.0, 5.0, n_ref)
drifted_part = RNG.normal(130.0, 5.0, n - n_ref)
value = np.concatenate([stable_part, drifted_part])
df_daily = pd.DataFrame({
    "day": pd.date_range("2024-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
    "metric_value": value.round(4),
    "drift_start_row": [100] * n,
})
df_daily.to_csv(OUT / "daily_metrics_dirty.csv", index=False)
print(f"daily_metrics_dirty.csv: {len(df_daily)} rows, drift at row 100")

# ---------------------------------------------------------------------------
# edge_cases.csv
# ---------------------------------------------------------------------------
df_edge = pd.DataFrame({
    "future_ts": ["2099-01-01T00:00:00", "2099-06-15T12:00:00", "2099-12-31T23:59:59"],
    "null_value": [None, 1.5, None],
    "zero_value": [0.0, 0.0, 0.0],
    "constant_value": [42.0, 42.0, 42.0],
    "normal_value": [1.0, 2.0, 3.0],
})
df_edge.to_csv(OUT / "edge_cases.csv", index=False)
print(f"edge_cases.csv: {len(df_edge)} rows")

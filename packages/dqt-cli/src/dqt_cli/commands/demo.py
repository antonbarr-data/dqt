"""Demo data generation commands."""
from __future__ import annotations

import shutil
from pathlib import Path

import typer

_DEMO_DIR = Path("demo")


def seed_command() -> None:
    """Generate synthetic demo data (fct_orders, fct_sessions) and a starter checks.yaml."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)
    n = 500
    _DEMO_DIR.mkdir(exist_ok=True)

    # fct_orders: lognormal revenue, categorical status, ~2% null customer_id
    orders = pd.DataFrame({
        "order_id": range(1, n + 1),
        "amount_usd": rng.lognormal(5.0, 0.5, n).round(2),
        "status": rng.choice(["completed", "cancelled", "pending", "refunded"], n),
        "customer_id": rng.integers(1, 200, n).astype(float),
        "created_at": pd.date_range("2024-01-01", periods=n, freq="1h").astype(str),
    })
    null_idx = rng.choice(n, size=int(n * 0.02), replace=False)
    orders.loc[null_idx, "customer_id"] = None

    # fct_sessions: heavy-tailed duration
    sessions = pd.DataFrame({
        "session_id": range(1, n + 1),
        "duration_s": rng.lognormal(4.0, 1.2, n).round(1),
        "page_views": rng.integers(1, 40, n),
        "user_id": rng.integers(1, 300, n),
    })

    orders.to_csv(_DEMO_DIR / "fct_orders.csv", index=False)
    sessions.to_csv(_DEMO_DIR / "fct_sessions.csv", index=False)

    (_DEMO_DIR / "checks.yaml").write_text("""\
version: "1"
source:
  type: csv
  id: orders
  path: demo/fct_orders.csv
  table_name: fct_orders
checks:
  - schema_name: public
    table_name: fct_orders
    column_name: customer_id
    detector_slug: null_fraction
  - schema_name: public
    table_name: fct_orders
    column_name: amount_usd
    detector_slug: mad_outlier_fraction
  - schema_name: public
    table_name: fct_orders
    column_name: status
    detector_slug: set_membership
    params:
      allowed_values: [completed, cancelled, pending, refunded]
""")
    typer.echo(f"Seeded demo/ — fct_orders.csv and fct_sessions.csv ({n} rows each)")
    typer.echo("Run: dqt run demo/checks.yaml")


def reset_command() -> None:
    """Remove all files in demo/."""
    if _DEMO_DIR.exists():
        shutil.rmtree(_DEMO_DIR)
        typer.echo("Demo data removed.")
    else:
        typer.echo("Nothing to reset.")

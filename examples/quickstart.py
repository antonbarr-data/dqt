"""
dqt quickstart — minimal end-to-end example.

Connects to a Postgres warehouse, samples a column, runs distribution + drift
detectors, and prints the verdicts. Designed to run with no extras beyond the
core library + dqt[postgres].

Usage:
    pip install 'dqt[postgres]'
    DQT_PG_HOST=... DQT_PG_DB=... python examples/quickstart.py
"""

from __future__ import annotations

import os

from dqt.adapters import postgres
from dqt.algorithms import (
    PSI,  # stability
    KS2Sample,  # distribution shape change
    Wasserstein1,  # level shift
)
from dqt.checks import Baseline, Check, RollingWindow
from dqt.runner import Runner
from dqt.store import MemoryStore


def main() -> None:
    src = postgres.connect(
        host=os.environ["DQT_PG_HOST"],
        port=int(os.environ.get("DQT_PG_PORT", 5432)),
        database=os.environ["DQT_PG_DB"],
        user=os.environ["DQT_PG_USER"],
        password=os.environ["DQT_PG_PASSWORD"],
        ssl="require",
    )

    health = src.health_check()
    for step in health.steps:
        print(f"  [{step.status}] {step.name}  ({step.latency_ms} ms)")
    if not health.ok:
        raise SystemExit("Health check failed; fix connection before continuing.")

    # Sample 100k rows from a fact table
    sample = src.sample("public", "fct_orders", n=100_000)
    print(f"Sampled {len(sample):,} rows from fct_orders")

    # Three checks on order_total
    column = "order_total"
    baseline = Baseline(kind="rolling", window=RollingWindow(days=14))

    checks = [
        Check(
            id=f"orders.{column}.shape_change",
            source=src.id,
            dataset="public.fct_orders",
            column=column,
            detector=KS2Sample.slug,
            baseline=baseline,
        ),
        Check(
            id=f"orders.{column}.level_shift",
            source=src.id,
            dataset="public.fct_orders",
            column=column,
            detector=Wasserstein1.slug,
            baseline=baseline,
        ),
        Check(
            id=f"orders.{column}.stability",
            source=src.id,
            dataset="public.fct_orders",
            column=column,
            detector=PSI.slug,
            baseline=baseline,
        ),
    ]

    store = MemoryStore()
    runner = Runner(store=store)

    for check in checks:
        result = runner.run(check, source=src)
        r = result.detector_result
        print(f"{result.check_id:<44} {r.verdict:<5} score={r.score:.4f}  ({r.plain_english})")

    # Show what an incident would look like (if any check failed)
    incidents = store.list_incidents()
    if incidents:
        print(f"\n{len(incidents)} incident(s) opened:")
        for inc in incidents:
            print(f"  - {inc.id}  {inc.detector}  score={inc.score:.4f}")
    else:
        print("\nAll checks passed. Quiet warehouse today.")


if __name__ == "__main__":
    main()

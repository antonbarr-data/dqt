# packages/dqt-cli/src/dqt_cli/commands/healthcheck.py
"""dqt healthcheck -- verify the local dqt installation is working."""
import sys
import typer


def healthcheck_command() -> None:
    """Run a quick sanity check on the dqt installation."""
    checks = []

    # 1. Import dqt
    try:
        import dqt
        checks.append(("dqt import", True, f"v{dqt.__version__}"))
    except Exception as e:
        checks.append(("dqt import", False, str(e)))

    # 2. Registry
    try:
        from dqt.algorithms._registry import registry
        n = len(registry.slugs())
        checks.append(("detector registry", True, f"{n} detectors"))
    except Exception as e:
        checks.append(("detector registry", False, str(e)))

    # 3. MemoryStore round-trip
    try:
        from dqt.store.memory import MemoryStore
        from dqt.store._protocol import RunResult
        from dqt.algorithms._base import Verdict
        from datetime import datetime, timezone
        from uuid import uuid4
        store = MemoryStore()
        now = datetime.now(timezone.utc)
        run = RunResult(
            run_id=uuid4(), check_id=uuid4(), detector_slug="ks_pvalue",
            detector_version="1", started_at=now, finished_at=now,
            verdict=Verdict.pass_, score=0.1, plain_english="ok", details={},
        )
        store.save_run(run)
        checks.append(("MemoryStore round-trip", True, "ok"))
    except Exception as e:
        checks.append(("MemoryStore round-trip", False, str(e)))

    # 4. ProofBundle
    try:
        from dqt.store.proof import ProofBundle, compute_proof, verify_proof
        import pandas as pd
        from dqt.store._protocol import RunResult
        from dqt.algorithms._base import Verdict
        from datetime import datetime, timezone
        from uuid import uuid4
        now = datetime.now(timezone.utc)
        run = RunResult(
            run_id=uuid4(), check_id=uuid4(), detector_slug="ks_pvalue",
            detector_version="1", started_at=now, finished_at=now,
            verdict=Verdict.pass_, score=0.1, plain_english="ok", details={},
        )
        df = pd.DataFrame({"x": [1, 2, 3]})
        proof = compute_proof(run, df)
        assert verify_proof(proof, run, df)
        checks.append(("ProofBundle round-trip", True, "ok"))
    except Exception as e:
        checks.append(("ProofBundle round-trip", False, str(e)))

    all_ok = all(ok for _, ok, _ in checks)
    for name, ok, detail in checks:
        status = "ok" if ok else "FAIL"
        typer.echo(f"  [{status}] {name}: {detail}")

    if all_ok:
        typer.echo("healthcheck passed")
    else:
        typer.echo("healthcheck FAILED", err=True)
        raise typer.Exit(code=1)

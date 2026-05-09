import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest


def test_verdict_values():
    from dqt.algorithms._base import Verdict
    assert Verdict.pass_.value == "pass"
    assert Verdict.warn.value == "warn"
    assert Verdict.fail.value == "fail"


def test_detector_result_fields():
    from dqt.algorithms._base import DetectorResult, Verdict
    r = DetectorResult(score=0.5, verdict=Verdict.pass_, plain_english="all good")
    assert r.score == 0.5
    assert r.details == {}


def test_agg_expr_fields():
    from dqt.adapters._protocol import AggExpr
    e = AggExpr(name="null_count", sql="COUNT(*) - COUNT(col)")
    assert e.name == "null_count"


def test_health_check_result_passed():
    from dqt.adapters._protocol import HealthCheckResult, HealthCheckStep
    steps = [
        HealthCheckStep(name="tcp", status="pass", latency_ms=1.0, detail="ok"),
        HealthCheckStep(name="auth", status="pass", latency_ms=2.0, detail="ok"),
    ]
    result = HealthCheckResult(steps=steps)
    assert result.passed is True


def test_health_check_result_failed():
    from dqt.adapters._protocol import HealthCheckResult, HealthCheckStep
    steps = [
        HealthCheckStep(name="tcp", status="pass", latency_ms=1.0, detail="ok"),
        HealthCheckStep(name="auth", status="fail", latency_ms=0.0, detail="bad password"),
    ]
    result = HealthCheckResult(steps=steps)
    assert result.passed is False


def test_run_result_fields():
    from dqt.algorithms._base import Verdict
    from dqt.store._protocol import RunResult
    now = datetime.now(timezone.utc)
    check_id = uuid.uuid4()
    r = RunResult(
        check_id=check_id,
        detector_slug="completeness",
        started_at=now,
        finished_at=now,
        verdict=Verdict.pass_,
        score=0.99,
        plain_english="99% complete",
    )
    assert r.run_id is not None
    assert r.details == {}


def test_incident_fields():
    from dqt.algorithms._base import Verdict
    from dqt.store._protocol import Incident
    now = datetime.now(timezone.utc)
    inc = Incident(
        check_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        detector_slug="completeness",
        severity=Verdict.fail,
        opened_at=now,
        score=0.7,
    )
    assert inc.status == "open"
    assert inc.resolved_at is None


def test_check_model_fields():
    from dqt.checks.models import BaselineConfig, Check
    check = Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
    )
    assert check.sample_n == 100_000
    assert check.baseline is None


def test_check_with_baseline():
    from dqt.checks.models import BaselineConfig, Check
    check = Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
        baseline=BaselineConfig(window_days=14),
    )
    assert check.baseline.window_days == 14
    assert check.baseline.min_rows == 1_000


def test_get_logger():
    from dqt.utils.logging import get_logger
    log = get_logger("dqt.test")
    assert log is not None

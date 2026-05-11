import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.mark.unit
def test_to_bundle_writes_expected_files(tmp_path):
    """RunResult.to_bundle() creates result.json, config.json, environment.json."""
    from dqt.store._protocol import RunResult, ReproducibilityBundle
    from dqt.algorithms._base import Verdict

    bundle = ReproducibilityBundle(
        check_id=uuid4(),
        run_id=uuid4(),
        detector_slug="iqr_fence",
        detector_params={"k": 3.0},
        schema_name="analytics",
        table_name="orders",
        column_name="amount",
        sample_n=100,
    )
    run = RunResult(
        check_id=bundle.check_id,
        detector_slug="iqr_fence",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        verdict=Verdict.fail,
        score=0.12,
        plain_english="12% of values outside IQR fences",
        details={"outlier_fraction": 0.12},
        reproducibility=bundle,
    )

    run.to_bundle(tmp_path)

    assert (tmp_path / "result.json").exists()
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "environment.json").exists()

    result_data = json.loads((tmp_path / "result.json").read_text())
    assert result_data["verdict"] == "fail"
    assert result_data["score"] == 0.12

    env_data = json.loads((tmp_path / "environment.json").read_text())
    assert "dqt_version" in env_data
    assert "python_version" in env_data


@pytest.mark.unit
def test_to_bundle_writes_diagnostic_sql(tmp_path):
    """diagnostic.sql is written only when RunResult.diagnostic_sql is set."""
    from dqt.store._protocol import RunResult
    from dqt.algorithms._base import Verdict

    run = RunResult(
        check_id=uuid4(),
        detector_slug="iqr_fence",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        verdict=Verdict.warn,
        score=0.05,
        plain_english="5% outside fences",
        diagnostic_sql="SELECT * FROM orders WHERE amount > 1000",
    )

    run.to_bundle(tmp_path)

    assert (tmp_path / "diagnostic.sql").exists()
    assert "SELECT" in (tmp_path / "diagnostic.sql").read_text()


@pytest.mark.unit
def test_to_bundle_no_diagnostic_sql(tmp_path):
    """diagnostic.sql is absent when RunResult.diagnostic_sql is None."""
    from dqt.store._protocol import RunResult
    from dqt.algorithms._base import Verdict

    run = RunResult(
        check_id=uuid4(),
        detector_slug="iqr_fence",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        verdict=Verdict.pass_,
        score=0.01,
        plain_english="All good",
    )

    run.to_bundle(tmp_path)

    assert not (tmp_path / "diagnostic.sql").exists()

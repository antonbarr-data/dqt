# packages/dqt/tests/test_detector_versioning.py
"""Tests for detector versioning in RunResult and Runner auto-refit on version change."""
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

import dqt
from dqt.algorithms._base import BaseDetector
from dqt.algorithms._registry import registry
from dqt.store._protocol import RunResult


def _make_check(slug: str = "completeness", col: str = "amount") -> dqt.Check:
    return dqt.Check(
        schema_name="public",
        table_name="orders",
        column_name=col,
        detector_slug=slug,
    )


def _mock_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.sample.return_value = pd.DataFrame({"amount": list(range(200))})
    adapter.aggregate.return_value = {"null_count": 0, "total_count": 200}
    adapter.describe_columns.return_value = [MagicMock(name="amount", row_count=200)]
    return adapter


def test_base_detector_has_version():
    cls = registry.get("completeness")
    assert hasattr(cls, "version")
    assert isinstance(cls.version, str)
    assert cls.version != ""


def test_all_registered_detectors_have_version():
    for slug in registry.slugs():
        cls = registry.get(slug)
        assert hasattr(cls, "version"), f"{slug} missing ClassVar version"
        assert isinstance(cls.version, str)


def test_run_result_has_detector_version():
    check = _make_check()
    adapter = _mock_adapter()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    result = runner.run(check, adapter)
    assert isinstance(result, RunResult)
    assert result.detector_version != ""


def test_run_result_detector_version_matches_cls():
    check = _make_check("completeness")
    adapter = _mock_adapter()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    result = runner.run(check, adapter)
    cls = registry.get("completeness")
    assert result.detector_version == cls.version


def test_runner_refits_when_version_changes():
    """Simulate an algorithm update: cached state has old version, detector now reports new version."""
    check = _make_check("completeness")
    adapter = _mock_adapter()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)

    # First run: fit + score; state is cached as ("1", ...)
    runner.run(check, adapter)
    assert check.id in runner._states
    fit_count_before = adapter.aggregate.call_count

    # Simulate algorithm version bump: patch cls.version to "2"
    cls = registry.get("completeness")
    with patch.object(cls, "version", new="2"):
        runner.run(check, adapter)
        fit_count_after = adapter.aggregate.call_count

    # A re-fit means aggregate was called again (aggregate detectors use adapter.aggregate for fit)
    assert fit_count_after > fit_count_before


def test_run_result_detector_version_after_refit():
    """After auto-refit the stored RunResult carries the new version."""
    check = _make_check("completeness")
    adapter = _mock_adapter()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)

    runner.run(check, adapter)

    cls = registry.get("completeness")
    with patch.object(cls, "version", new="99"):
        result = runner.run(check, adapter)

    assert result.detector_version == "99"


def test_to_bundle_includes_detector_version(tmp_path):
    check = _make_check("completeness")
    adapter = _mock_adapter()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    result = runner.run(check, adapter)
    result.to_bundle(tmp_path)

    import json
    data = json.loads((tmp_path / "result.json").read_text())
    assert "detector_version" in data
    assert data["detector_version"] == result.detector_version


def test_default_run_result_detector_version():
    """RunResult created without explicit detector_version defaults to '1'."""
    from datetime import datetime, timezone
    from uuid import uuid4
    rr = RunResult(
        check_id=uuid4(),
        detector_slug="completeness",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        verdict=dqt.Verdict.pass_,
        score=0.0,
        plain_english="ok",
    )
    assert rr.detector_version == "1"

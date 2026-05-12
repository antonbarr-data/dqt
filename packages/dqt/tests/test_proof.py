# packages/dqt/tests/test_proof.py
"""Tests for ProofBundle cryptographic commitment (store/proof.py)."""
import pytest
import pandas as pd
from uuid import uuid4
from datetime import timezone

from dqt.store.proof import (
    ProofBundle,
    _hash_dataframe,
    compute_proof,
    verify_proof,
)
from dqt.store._protocol import RunResult
from dqt.algorithms._base import Verdict


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_run_result(**kwargs) -> RunResult:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    defaults = dict(
        run_id=uuid4(),
        check_id=uuid4(),
        detector_slug="ks_2sample",
        detector_version="1",
        verdict=Verdict.pass_,
        score=0.42,
        plain_english="no drift detected",
        started_at=now,
        finished_at=now,
        details={},
    )
    defaults.update(kwargs)
    return RunResult(**defaults)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


# ---------------------------------------------------------------------------
# _hash_dataframe — stability tests
# ---------------------------------------------------------------------------

def test_hash_row_order_independent():
    df1 = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    df2 = pd.DataFrame({"a": [3, 1, 2], "b": ["z", "x", "y"]})
    assert _hash_dataframe(df1) == _hash_dataframe(df2)


def test_hash_column_order_independent():
    df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    df2 = pd.DataFrame({"b": [3, 4], "a": [1, 2]})
    assert _hash_dataframe(df1) == _hash_dataframe(df2)


def test_hash_changes_on_value_change():
    df1 = _sample_df()
    df2 = pd.DataFrame({"a": [1, 2, 99], "b": ["x", "y", "z"]})
    assert _hash_dataframe(df1) != _hash_dataframe(df2)


def test_hash_returns_64_char_hex():
    h = _hash_dataframe(_sample_df())
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# ProofBundle dataclass
# ---------------------------------------------------------------------------

def test_proof_bundle_to_dict_fields():
    run = _make_run_result()
    df = _sample_df()
    proof = compute_proof(run, df)
    d = proof.to_dict()
    assert d["run_id"] == str(run.run_id)
    assert d["check_id"] == str(run.check_id)
    assert d["detector_slug"] == run.detector_slug
    assert d["detector_version"] == run.detector_version
    assert d["row_count"] == len(df)
    assert d["commitment_algorithm"] == "sha256"
    assert "data_hash" in d
    assert "commitment" in d
    assert "computed_at" in d


def test_proof_bundle_computed_at_is_utc():
    run = _make_run_result()
    proof = compute_proof(run, _sample_df())
    assert proof.computed_at.tzinfo is not None
    assert proof.computed_at.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# compute_proof
# ---------------------------------------------------------------------------

def test_compute_proof_deterministic():
    run = _make_run_result()
    df = _sample_df()
    p1 = compute_proof(run, df)
    p2 = compute_proof(run, df)
    assert p1.data_hash == p2.data_hash
    assert p1.commitment == p2.commitment


def test_compute_proof_commitment_is_64_char_hex():
    run = _make_run_result()
    proof = compute_proof(run, _sample_df())
    assert len(proof.commitment) == 64
    assert all(c in "0123456789abcdef" for c in proof.commitment)


def test_compute_proof_row_count():
    run = _make_run_result()
    df = pd.DataFrame({"x": range(17)})
    proof = compute_proof(run, df)
    assert proof.row_count == 17


def test_compute_proof_different_verdicts_produce_different_commitments():
    check_id = uuid4()
    run_pass = _make_run_result(check_id=check_id, verdict=Verdict.pass_, score=0.1)
    run_fail = _make_run_result(
        run_id=run_pass.run_id,
        check_id=check_id,
        verdict=Verdict.fail,
        score=0.1,
    )
    df = _sample_df()
    p1 = compute_proof(run_pass, df)
    p2 = compute_proof(run_fail, df)
    assert p1.commitment != p2.commitment


# ---------------------------------------------------------------------------
# verify_proof
# ---------------------------------------------------------------------------

def test_verify_proof_valid():
    run = _make_run_result()
    df = _sample_df()
    proof = compute_proof(run, df)
    assert verify_proof(proof, run, df) is True


def test_verify_proof_tampered_data():
    run = _make_run_result()
    df = _sample_df()
    proof = compute_proof(run, df)
    df_tampered = pd.DataFrame({"a": [1, 2, 99], "b": ["x", "y", "z"]})
    assert verify_proof(proof, run, df_tampered) is False


def test_verify_proof_tampered_score():
    run = _make_run_result(score=0.42)
    df = _sample_df()
    proof = compute_proof(run, df)
    run_tampered = _make_run_result(
        run_id=run.run_id,
        check_id=run.check_id,
        score=0.99,
        verdict=run.verdict,
    )
    assert verify_proof(proof, run_tampered, df) is False


def test_verify_proof_tampered_verdict():
    run = _make_run_result(verdict=Verdict.pass_)
    df = _sample_df()
    proof = compute_proof(run, df)
    run_tampered = _make_run_result(
        run_id=run.run_id,
        check_id=run.check_id,
        score=run.score,
        verdict=Verdict.fail,
    )
    assert verify_proof(proof, run_tampered, df) is False


def test_verify_proof_tampered_commitment_field():
    run = _make_run_result()
    df = _sample_df()
    proof = compute_proof(run, df)
    # Manually corrupt the commitment
    bad_proof = ProofBundle(
        run_id=proof.run_id,
        check_id=proof.check_id,
        detector_slug=proof.detector_slug,
        detector_version=proof.detector_version,
        data_hash=proof.data_hash,
        row_count=proof.row_count,
        commitment="a" * 64,
    )
    assert verify_proof(bad_proof, run, df) is False

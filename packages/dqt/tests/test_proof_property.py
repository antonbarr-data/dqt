# packages/dqt/tests/test_proof_property.py
"""Property-based tests for compute_proof / verify_proof (C.12)."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from dqt.algorithms._base import Verdict
from dqt.store._protocol import RunResult
from dqt.store.proof import ProofBundle, compute_proof, verify_proof


def _now():
    return datetime.now(timezone.utc)


def _run(**kwargs):
    defaults = dict(
        run_id=uuid4(), check_id=uuid4(), detector_slug="ks_pvalue",
        detector_version="1", started_at=_now(), finished_at=_now(),
        verdict=Verdict.pass_, score=0.42, plain_english="ok", details={},
    )
    defaults.update(kwargs)
    return RunResult(**defaults)


_verdicts = st.sampled_from(list(Verdict))
_scores = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_slugs = st.sampled_from(["ks_pvalue", "mad_outlier_fraction", "psi"])


@st.composite
def run_and_df(draw):
    verdict = draw(_verdicts)
    score = draw(_scores)
    slug = draw(_slugs)
    n_rows = draw(st.integers(min_value=1, max_value=100))
    n_cols = draw(st.integers(min_value=1, max_value=5))
    data = {f"col_{i}": list(range(n_rows)) for i in range(n_cols)}
    df = pd.DataFrame(data)
    run = _run(verdict=verdict, score=score, detector_slug=slug)
    return run, df


@given(run_and_df())
@settings(max_examples=100)
def test_verify_proof_roundtrip(run_df):
    run, df = run_df
    proof = compute_proof(run, df)
    assert verify_proof(proof, run, df) is True


@given(run_and_df())
@settings(max_examples=50)
def test_reordering_rows_does_not_change_data_hash(run_df):
    run, df = run_df
    proof = compute_proof(run, df)
    shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)
    proof_shuffled = compute_proof(run, shuffled)
    assert proof.data_hash == proof_shuffled.data_hash


@given(run_and_df())
@settings(max_examples=50)
def test_reordering_columns_does_not_change_data_hash(run_df):
    run, df = run_df
    if len(df.columns) < 2:
        return
    proof = compute_proof(run, df)
    reversed_cols = df[list(reversed(list(df.columns)))]
    proof_reordered = compute_proof(run, reversed_cols)
    assert proof.data_hash == proof_reordered.data_hash


@given(run_and_df(), _verdicts)
@settings(max_examples=50)
def test_changing_verdict_invalidates_proof(run_df, other_verdict):
    run, df = run_df
    proof = compute_proof(run, df)
    tampered_run = _run(
        run_id=run.run_id, check_id=run.check_id,
        detector_slug=run.detector_slug, score=run.score,
        verdict=other_verdict,
    )
    if other_verdict == run.verdict:
        assert verify_proof(proof, tampered_run, df) is True
    else:
        assert verify_proof(proof, tampered_run, df) is False


@given(run_and_df(), _scores)
@settings(max_examples=50)
def test_changing_score_invalidates_proof(run_df, other_score):
    run, df = run_df
    proof = compute_proof(run, df)
    tampered_run = _run(
        run_id=run.run_id, check_id=run.check_id,
        detector_slug=run.detector_slug, verdict=run.verdict,
        score=other_score,
    )
    if abs(other_score - run.score) < 1e-10:
        assert verify_proof(proof, tampered_run, df) is True
    else:
        assert verify_proof(proof, tampered_run, df) is False

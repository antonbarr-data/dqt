# packages/dqt/src/dqt/store/proof.py
"""Provable correctness for declarative checks.

A ProofBundle cryptographically binds a RunResult to the sample data it was
computed from. Anyone with the sample can re-derive the data_hash and verify
the commitment — proving that a given verdict was produced from specific data
by a specific algorithm version, without re-running the check.

Commitment algorithm:
  SHA-256 of a canonical JSON encoding of:
  (run_id, check_id, detector_slug, detector_version, data_hash, verdict, score)

Data hash:
  SHA-256 of the row-sorted, tab-separated sample (stable across column order
  by sorting columns alphabetically before hashing).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    import pandas as pd
    from dqt.checks.models import Check
    from dqt.store._protocol import RunResult


@dataclass
class ProofBundle:
    """Cryptographic proof that a RunResult was computed from a specific sample."""
    run_id: UUID
    check_id: UUID
    detector_slug: str
    detector_version: str
    # SHA-256 hex digest of the row-sorted sample data
    data_hash: str
    row_count: int
    # SHA-256 commitment over (run_id, check_id, slug, version, data_hash, verdict, score)
    commitment: str
    commitment_algorithm: str = "sha256"
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "run_id": str(self.run_id),
            "check_id": str(self.check_id),
            "detector_slug": self.detector_slug,
            "detector_version": self.detector_version,
            "data_hash": self.data_hash,
            "row_count": self.row_count,
            "commitment": self.commitment,
            "commitment_algorithm": self.commitment_algorithm,
            "computed_at": self.computed_at.isoformat(),
        }


def _hash_dataframe(df: "pd.DataFrame") -> str:
    """Compute a stable SHA-256 hash of a DataFrame.

    Columns are sorted alphabetically. Rows are sorted lexicographically by
    all values (as strings) to be independent of fetch order. Values are
    tab-separated; rows are newline-separated.
    """
    cols = sorted(df.columns.tolist())
    rows = df[cols].astype(str).values.tolist()
    rows.sort()
    serialised = "\n".join("\t".join(row) for row in rows)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def _commitment_input(
    run_id: UUID,
    check_id: UUID,
    detector_slug: str,
    detector_version: str,
    data_hash: str,
    verdict: str,
    score: float,
) -> str:
    """Build the canonical JSON string used as SHA-256 commitment input."""
    payload = {
        "run_id": str(run_id),
        "check_id": str(check_id),
        "detector_slug": detector_slug,
        "detector_version": detector_version,
        "data_hash": data_hash,
        "verdict": verdict,
        "score": round(score, 10),  # round to avoid float serialisation variance
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_proof(run_result: "RunResult", sample_df: "pd.DataFrame") -> ProofBundle:
    """Compute a ProofBundle binding a RunResult to the sample it was scored on.

    Args:
        run_result: The RunResult returned by Runner.run().
        sample_df: The DataFrame that was passed to detector.score().

    Returns:
        ProofBundle with data_hash and commitment.
    """
    data_hash = _hash_dataframe(sample_df)
    commitment_str = _commitment_input(
        run_id=run_result.run_id,
        check_id=run_result.check_id,
        detector_slug=run_result.detector_slug,
        detector_version=run_result.detector_version,
        data_hash=data_hash,
        verdict=run_result.verdict.value,
        score=run_result.score,
    )
    commitment = hashlib.sha256(commitment_str.encode("utf-8")).hexdigest()
    return ProofBundle(
        run_id=run_result.run_id,
        check_id=run_result.check_id,
        detector_slug=run_result.detector_slug,
        detector_version=run_result.detector_version,
        data_hash=data_hash,
        row_count=len(sample_df),
        commitment=commitment,
    )


def verify_proof(
    proof: ProofBundle,
    run_result: "RunResult",
    sample_df: "pd.DataFrame",
) -> bool:
    """Verify that a ProofBundle is consistent with a RunResult and sample.

    Recomputes the commitment from the provided inputs and compares to the
    stored commitment. Returns True iff they match.

    Args:
        proof: The ProofBundle to verify.
        run_result: The RunResult to verify against.
        sample_df: The sample DataFrame to hash.

    Returns:
        True if the proof is valid; False if any input was tampered with.
    """
    recomputed = compute_proof(run_result, sample_df)
    return (
        proof.data_hash == recomputed.data_hash
        and proof.commitment == recomputed.commitment
        and proof.row_count == recomputed.row_count
    )

# packages/dqt/src/dqt/causality/review.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CausalReviewEdge:
    id: str
    cause: str
    effect: str
    p_value: float
    evidence_strength: str          # "none" | "weak" | "moderate" | "strong"
    status: str = "pending"         # "pending" | "accepted" | "rejected"
    reviewer: str = ""
    notes: str = ""
    weight_delta: float = 0.0       # +0.2 on accept, applied by causal queries


class ReviewStore:
    """In-memory store for causal edge review decisions."""

    def __init__(self) -> None:
        self._edges: dict[str, CausalReviewEdge] = {}

    def add(self, edge: CausalReviewEdge) -> None:
        self._edges[edge.id] = edge

    def review(
        self,
        edge_id: str,
        decision: Literal["accept", "reject"],
        reviewer: str,
        notes: str = "",
    ) -> CausalReviewEdge:
        if edge_id not in self._edges:
            raise KeyError(f"Edge {edge_id!r} not found")
        edge = self._edges[edge_id]
        edge.status = "accepted" if decision == "accept" else "rejected"
        edge.reviewer = reviewer
        edge.notes = notes
        edge.weight_delta = 0.2 if decision == "accept" else 0.0
        return edge

    def list_pending(self, limit: int = 20) -> list[CausalReviewEdge]:
        pending = [e for e in self._edges.values() if e.status == "pending"]
        return pending[:limit]

    def list_by_status(self, status: str) -> list[CausalReviewEdge]:
        return [e for e in self._edges.values() if e.status == status]

    def stats(self) -> dict:
        all_edges = list(self._edges.values())
        total = len(all_edges)
        accepted = sum(1 for e in all_edges if e.status == "accepted")
        rejected = sum(1 for e in all_edges if e.status == "rejected")
        pending = sum(1 for e in all_edges if e.status == "pending")
        reviewed = accepted + rejected
        accept_rate = accepted / reviewed if reviewed > 0 else 0.0
        return {
            "total": total,
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
            "accept_rate": accept_rate,
        }

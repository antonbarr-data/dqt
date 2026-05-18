"use client";

import { useState, useEffect, useCallback } from "react";
import { Network, RefreshCw, Check, X } from "lucide-react";

interface ReviewEdge {
  id: string;
  cause: string;
  effect: string;
  p_value: number;
  evidence_strength: string;
  status: string;
  reviewer: string;
  notes: string;
}

interface Stats {
  total: number;
  pending: number;
  accepted: number;
  rejected: number;
  accept_rate: number;
}

const STRENGTH_COLOR: Record<string, string> = {
  strong: "var(--pass)",
  moderate: "var(--warn)",
  weak: "var(--fg-3)",
};

export default function CausalityPage() {
  const [edges, setEdges] = useState<ReviewEdge[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);
  const [recomputeResult, setRecomputeResult] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<ReviewEdge | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewing, setReviewing] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [qRes, sRes] = await Promise.all([
        fetch(`/api/v1/causal/review/queue?status=${statusFilter}&limit=50`),
        fetch("/api/v1/causal/review/stats"),
      ]);
      if (qRes.ok) setEdges(await qRes.json());
      if (sRes.ok) setStats(await sRes.json());
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleRecompute() {
    setRecomputing(true);
    setRecomputeResult(null);
    try {
      const res = await fetch("/api/v1/causal/recompute", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setRecomputeResult(`Analyzed ${data.metrics_analyzed} metrics, queued ${data.edges_queued} new edges`);
        await loadData();
      }
    } finally {
      setRecomputing(false);
    }
  }

  async function handleReview(decision: "accept" | "reject") {
    if (!selectedEdge) return;
    setReviewing(true);
    try {
      const res = await fetch(`/api/v1/causal/review/${encodeURIComponent(selectedEdge.id)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, reviewer: "user", notes: reviewNotes }),
      });
      if (res.ok) {
        setSelectedEdge(null);
        setReviewNotes("");
        await loadData();
      }
    } finally {
      setReviewing(false);
    }
  }

  const statusColors: Record<string, string> = {
    pending: "var(--warn)",
    accepted: "var(--pass)",
    rejected: "var(--fail)",
  };

  return (
    <div className="flex h-full">
      {/* main panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-line flex-shrink-0">
          <Network size={16} strokeWidth={1.6} style={{ color: "var(--fg-2)" }} />
          <span className="t-h2 flex-1" style={{ color: "var(--fg-0)" }}>Causality</span>
          <button
            onClick={handleRecompute}
            disabled={recomputing}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2 disabled:opacity-50"
            style={{ color: "var(--fg-1)" }}
          >
            <RefreshCw size={11} strokeWidth={1.6} className={recomputing ? "animate-spin" : ""} />
            {recomputing ? "Discovering..." : "Run discovery"}
          </button>
        </div>

        {/* stat bar */}
        {stats && (
          <div className="flex items-center gap-6 px-6 py-3 border-b border-line flex-shrink-0" style={{ background: "var(--bg-1)" }}>
            <div>
              <span className="kpi-label" style={{ color: "var(--fg-3)" }}>TOTAL</span>
              <span className="block kpi-value" style={{ color: "var(--fg-0)", fontSize: 20 }}>{stats.total}</span>
            </div>
            <div>
              <span className="kpi-label" style={{ color: "var(--fg-3)" }}>PENDING</span>
              <span className="block kpi-value" style={{ color: "var(--warn)", fontSize: 20 }}>{stats.pending}</span>
            </div>
            <div>
              <span className="kpi-label" style={{ color: "var(--fg-3)" }}>ACCEPTED</span>
              <span className="block kpi-value" style={{ color: "var(--pass)", fontSize: 20 }}>{stats.accepted}</span>
            </div>
            <div>
              <span className="kpi-label" style={{ color: "var(--fg-3)" }}>REJECTED</span>
              <span className="block kpi-value" style={{ color: "var(--fail)", fontSize: 20 }}>{stats.rejected}</span>
            </div>
            <div>
              <span className="kpi-label" style={{ color: "var(--fg-3)" }}>ACCEPT RATE</span>
              <span className="block kpi-value" style={{ color: "var(--fg-0)", fontSize: 20 }}>{(stats.accept_rate * 100).toFixed(0)}%</span>
            </div>
            {recomputeResult && (
              <span className="t-micro ml-auto" style={{ color: "var(--pass)" }}>{recomputeResult}</span>
            )}
          </div>
        )}

        {/* filter tabs */}
        <div className="flex items-center gap-0 px-6 border-b border-line flex-shrink-0">
          {["pending", "accepted", "rejected"].map(s => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setSelectedEdge(null); }}
              className="px-4 py-2.5 t-small border-b-2 transition-colors capitalize"
              style={{
                borderBottomColor: statusFilter === s ? "var(--accent)" : "transparent",
                color: statusFilter === s ? "var(--fg-0)" : "var(--fg-3)",
              }}
            >
              {s}
            </button>
          ))}
        </div>

        {/* edge list */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <span className="t-small" style={{ color: "var(--fg-3)" }}>Loading...</span>
            </div>
          ) : edges.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <Network size={32} strokeWidth={1} style={{ color: "var(--fg-3)" }} />
              <p className="t-small" style={{ color: "var(--fg-3)" }}>No {statusFilter} edges.</p>
              {statusFilter === "pending" && (
                <p className="t-micro text-center" style={{ color: "var(--fg-3)", maxWidth: 320 }}>
                  Run causal discovery to propose new edges, or add metrics via the wizard.
                </p>
              )}
            </div>
          ) : (
            <table className="w-full" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr className="border-b border-line">
                  {["Cause", "Effect", "p-value", "Strength", "Status", ""].map((h, i) => (
                    <th
                      key={i}
                      className="px-4 py-2 t-micro text-left"
                      style={{ color: "var(--fg-3)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {edges.map(edge => (
                  <tr
                    key={edge.id}
                    className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors cursor-pointer"
                    style={{ background: selectedEdge?.id === edge.id ? "var(--accent-bg)" : undefined }}
                    onClick={() => { setSelectedEdge(edge); setReviewNotes(""); }}
                  >
                    <td className="px-4 py-2.5">
                      <span className="t-small font-mono" style={{ color: "var(--accent)" }}>{edge.cause}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{edge.effect}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="t-small font-mono" style={{ color: "var(--fg-1)" }}>{edge.p_value.toFixed(4)}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="t-small" style={{ color: STRENGTH_COLOR[edge.evidence_strength] ?? "var(--fg-2)" }}>
                        {edge.evidence_strength}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className="t-micro px-1.5 py-0.5"
                        style={{
                          background: statusColors[edge.status] + "18",
                          color: statusColors[edge.status] ?? "var(--fg-2)",
                        }}
                      >
                        {edge.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 t-small" style={{ color: "var(--fg-3)" }}>›</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* review panel */}
      {selectedEdge && (
        <div className="border-l border-line p-5 flex-shrink-0 flex flex-col" style={{ width: 340, background: "var(--bg-1)" }}>
          <div className="flex items-center justify-between mb-4">
            <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Review edge</span>
            <button onClick={() => setSelectedEdge(null)} style={{ color: "var(--fg-3)" }}>
              <X size={14} />
            </button>
          </div>

          <div className="space-y-3 mb-4">
            <div>
              <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Cause</span>
              <span className="t-small font-mono" style={{ color: "var(--accent)" }}>{selectedEdge.cause}</span>
            </div>
            <div>
              <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Effect</span>
              <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{selectedEdge.effect}</span>
            </div>
            <div className="flex gap-4">
              <div>
                <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>p-value</span>
                <span className="t-small font-mono" style={{ color: "var(--fg-1)" }}>{selectedEdge.p_value.toFixed(4)}</span>
              </div>
              <div>
                <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Strength</span>
                <span className="t-small" style={{ color: STRENGTH_COLOR[selectedEdge.evidence_strength] ?? "var(--fg-2)" }}>
                  {selectedEdge.evidence_strength}
                </span>
              </div>
            </div>
            {selectedEdge.reviewer && (
              <div>
                <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Reviewed by</span>
                <span className="t-small" style={{ color: "var(--fg-1)" }}>{selectedEdge.reviewer}</span>
              </div>
            )}
            {selectedEdge.notes && (
              <div>
                <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Notes</span>
                <span className="t-small" style={{ color: "var(--fg-1)" }}>{selectedEdge.notes}</span>
              </div>
            )}
          </div>

          {selectedEdge.status === "pending" && (
            <>
              <div className="mb-4">
                <label className="t-micro block mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Notes (optional)</label>
                <textarea
                  className="w-full px-2 py-1.5 t-small border border-line bg-transparent outline-none focus:border-accent resize-none"
                  style={{ color: "var(--fg-0)", height: 60 }}
                  value={reviewNotes}
                  onChange={e => setReviewNotes(e.target.value)}
                  placeholder="Reason for decision..."
                />
              </div>
              <div className="flex gap-2 mt-auto">
                <button
                  onClick={() => handleReview("accept")}
                  disabled={reviewing}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
                  style={{ background: "var(--pass)" + "18", borderColor: "var(--pass)", color: "var(--pass)" }}
                >
                  <Check size={11} strokeWidth={1.6} />
                  Accept
                </button>
                <button
                  onClick={() => handleReview("reject")}
                  disabled={reviewing}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
                  style={{ background: "var(--fail)" + "18", borderColor: "var(--fail)", color: "var(--fail)" }}
                >
                  <X size={11} strokeWidth={1.6} />
                  Reject
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

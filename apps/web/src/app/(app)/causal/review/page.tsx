"use client";

import { useState, useEffect } from "react";
import { CheckCircle, XCircle, Network } from "lucide-react";

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
  moderate: "var(--accent)",
  weak: "var(--warn)",
  none: "var(--fg-3)",
};

export default function CausalReviewPage() {
  const [edges, setEdges] = useState<ReviewEdge[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selected, setSelected] = useState<ReviewEdge | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  function loadQueue() {
    fetch("/api/v1/causal/review/queue?status=pending&limit=20")
      .then(r => r.json())
      .then(data => { setEdges(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
    fetch("/api/v1/causal/review/stats")
      .then(r => r.json())
      .then(data => setStats(data))
      .catch(() => {});
  }

  useEffect(() => { loadQueue(); }, []);

  async function decide(decision: "accept" | "reject") {
    if (!selected) return;
    setSubmitting(true);
    await fetch(`/api/v1/causal/review/${encodeURIComponent(selected.id)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reviewer: "demo", notes }),
    });
    setSelected(null);
    setNotes("");
    setSubmitting(false);
    loadQueue();
  }

  return (
    <div className="flex h-full">
      <div className="flex flex-col border-r border-line flex-shrink-0" style={{ width: 380 }}>
        <div className="flex items-center gap-3 px-5 py-4 border-b border-line flex-shrink-0">
          <Network size={16} strokeWidth={1.6} style={{ color: "var(--fg-2)" }} />
          <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Reviewer queue</h1>
        </div>
        {stats && (
          <div className="flex gap-6 px-5 py-3 border-b border-line flex-shrink-0" style={{ background: "var(--bg-2)" }}>
            {[
              { label: "Pending", val: stats.pending, color: "var(--warn)" },
              { label: "Accepted", val: stats.accepted, color: "var(--pass)" },
              { label: "Rejected", val: stats.rejected, color: "var(--fail)" },
              { label: "Accept rate", val: `${(stats.accept_rate * 100).toFixed(0)}%`, color: "var(--fg-1)" },
            ].map(s => (
              <div key={s.label}>
                <p className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>{s.label}</p>
                <p className="t-small font-mono font-medium" style={{ color: s.color }}>{s.val}</p>
              </div>
            ))}
          </div>
        )}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-5 space-y-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-14 border border-line" style={{ background: "var(--bg-2)", opacity: 0.5 }} />
              ))}
            </div>
          )}
          {!loading && edges.length === 0 && (
            <div className="p-8 text-center">
              <p className="t-small" style={{ color: "var(--fg-3)" }}>No pending edges. All caught up!</p>
            </div>
          )}
          {!loading && edges.map(e => (
            <button
              key={e.id}
              onClick={() => { setSelected(selected?.id === e.id ? null : e); setNotes(""); }}
              className="w-full text-left px-5 py-3 border-b border-line transition-colors hover:bg-bg-2"
              style={{ background: selected?.id === e.id ? "var(--bg-2)" : "var(--bg-1)" }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{e.cause}</span>
                    <span className="t-micro" style={{ color: "var(--fg-3)" }}>{"→"}</span>
                    <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{e.effect}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="t-micro" style={{ color: STRENGTH_COLOR[e.evidence_strength] ?? "var(--fg-3)" }}>
                      {e.evidence_strength}
                    </span>
                    <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
                      p={e.p_value.toFixed(3)}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={ev => {
                      ev.stopPropagation();
                      setSubmitting(true);
                      fetch(`/api/v1/causal/review/${encodeURIComponent(e.id)}`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ decision: "accept", reviewer: "demo", notes: "" }),
                      }).finally(() => { setSubmitting(false); loadQueue(); setSelected(null); });
                    }}
                    className="hover:opacity-70 transition-opacity"
                    title="Accept"
                    disabled={submitting}
                  >
                    <CheckCircle size={14} strokeWidth={1.6} style={{ color: "var(--pass)" }} />
                  </button>
                  <button
                    onClick={ev => {
                      ev.stopPropagation();
                      setSubmitting(true);
                      fetch(`/api/v1/causal/review/${encodeURIComponent(e.id)}`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ decision: "reject", reviewer: "demo", notes: "" }),
                      }).finally(() => { setSubmitting(false); loadQueue(); setSelected(null); });
                    }}
                    className="hover:opacity-70 transition-opacity"
                    title="Reject"
                    disabled={submitting}
                  >
                    <XCircle size={14} strokeWidth={1.6} style={{ color: "var(--fail)" }} />
                  </button>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 p-6 overflow-y-auto">
        {!selected && (
          <div className="flex items-center justify-center h-full">
            <p className="t-small" style={{ color: "var(--fg-3)" }}>Select an edge to review</p>
          </div>
        )}
        {selected && (
          <div className="max-w-lg">
            <h2 className="t-small font-medium mb-5" style={{ color: "var(--fg-0)" }}>Review edge</h2>
            <div className="border border-line p-4 mb-5" style={{ background: "var(--bg-2)" }}>
              <div className="flex items-center gap-3 mb-3">
                <span className="t-small font-mono" style={{ color: "var(--accent)" }}>{selected.cause}</span>
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>causes</span>
                <span className="t-small font-mono" style={{ color: "var(--accent)" }}>{selected.effect}</span>
              </div>
              <div className="flex gap-6">
                <div>
                  <p className="t-micro" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Evidence</p>
                  <p className="t-small font-mono" style={{ color: STRENGTH_COLOR[selected.evidence_strength] ?? "var(--fg-1)" }}>{selected.evidence_strength}</p>
                </div>
                <div>
                  <p className="t-micro" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>p-value</p>
                  <p className="t-small font-mono" style={{ color: "var(--fg-1)" }}>{selected.p_value.toFixed(4)}</p>
                </div>
              </div>
            </div>
            <div className="mb-5">
              <label className="t-micro block mb-1.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={3}
                className="w-full t-small px-3 py-2 border border-line bg-transparent outline-none resize-none focus:border-accent transition-colors"
                style={{ color: "var(--fg-0)" }}
                placeholder="Confounder? Spurious? Domain knowledge..."
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => decide("accept")}
                disabled={submitting}
                className="flex items-center gap-2 t-small px-4 py-2 border transition-opacity hover:opacity-80 disabled:opacity-40"
                style={{ background: "var(--accent-bg)", color: "var(--pass)", borderColor: "var(--pass)" }}
              >
                <CheckCircle size={13} strokeWidth={1.6} />
                Accept
              </button>
              <button
                onClick={() => decide("reject")}
                disabled={submitting}
                className="flex items-center gap-2 t-small px-4 py-2 border transition-opacity hover:opacity-80 disabled:opacity-40"
                style={{ background: "var(--fail-bg)", color: "var(--fail)", borderColor: "var(--fail)" }}
              >
                <XCircle size={13} strokeWidth={1.6} />
                Reject
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

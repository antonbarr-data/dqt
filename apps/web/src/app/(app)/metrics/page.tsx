"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Plus, Trash2, Loader2 } from "lucide-react";

interface MetricSummary {
  fqn: string;
  display_name: string;
  kind: string;
  dataset: string;
  owners: string[];
  tags: string[];
  current_verdict: string | null;
  last_run: string | null;
  pinned: boolean;
}

function VerdictDot({ verdict }: { verdict: string | null }) {
  const color =
    verdict === "pass" ? "var(--pass)" :
    verdict === "fail" ? "var(--fail)" :
    verdict === "warn" ? "var(--warn)" : "var(--fg-3)";
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8,
      background: color, boxShadow: `0 0 0 2px ${color}28`, flexShrink: 0,
    }} />
  );
}

const METRIC_KINDS = ["ratio", "count", "sum", "model"] as const;

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [confirmDeleteFqn, setConfirmDeleteFqn] = useState<string | null>(null);
  const [deletingFqn, setDeletingFqn] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formKind, setFormKind] = useState<"ratio" | "count" | "sum" | "model">("ratio");
  const [formDataset, setFormDataset] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadMetrics = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/metrics");
      if (res.ok) {
        setMetrics(await res.json());
      } else {
        setFetchError("Failed to load metrics.");
      }
    } catch {
      setFetchError("Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadMetrics(); }, [loadMetrics]);

  function handleDeleteMetric(fqn: string) {
    setDeletingFqn(true);
    fetch(`/api/v1/metrics/${encodeURIComponent(fqn)}`, { method: "DELETE" })
      .then(() => setMetrics((prev) => prev.filter((m) => m.fqn !== fqn)))
      .catch(() => {})
      .finally(() => { setDeletingFqn(false); setConfirmDeleteFqn(null); });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formName.trim() || !formDataset.trim()) {
      setFormError("Name and dataset are required.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const res = await fetch("/api/v1/metrics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: formName.trim(),
          kind: formKind,
          dataset: formDataset.trim(),
          description: formDescription.trim(),
        }),
      });
      if (res.status === 201) {
        setFormName("");
        setFormKind("ratio");
        setFormDataset("");
        setFormDescription("");
        setFormOpen(false);
        await loadMetrics();
      } else if (res.status === 409) {
        setFormError("A metric with this name already exists for that dataset.");
      } else {
        const err = await res.json().catch(() => ({}));
        setFormError(err.detail || "Failed to create metric.");
      }
    } catch {
      setFormError("Network error.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Metrics</h1>
        <div className="flex items-center gap-3">
          {!loading && (
            <span className="t-small" style={{ color: "var(--fg-3)" }}>{metrics.length} tracked</span>
          )}
          <button
            onClick={() => { setFormOpen((v) => !v); setFormError(null); }}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80"
            style={{
              background: formOpen ? "var(--accent-bg)" : "var(--bg-2)",
              color: formOpen ? "var(--accent)" : "var(--fg-0)",
              borderColor: formOpen ? "var(--accent)" : "var(--line-3)",
            }}
          >
            <Plus size={11} strokeWidth={1.6} />
            New metric
          </button>
        </div>
      </div>

      {/* New metric inline form */}
      {formOpen && (
        <form
          onSubmit={handleSubmit}
          className="mb-6 border border-line p-4 space-y-3"
          style={{ background: "var(--bg-1)" }}
        >
          <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>New metric</p>

          <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Name</label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Conversion rate"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              />
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Dataset</label>
              <input
                type="text"
                value={formDataset}
                onChange={(e) => setFormDataset(e.target.value)}
                placeholder="e.g. fct_orders"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              />
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Kind</label>
              <select
                value={formKind}
                onChange={(e) => setFormKind(e.target.value as typeof formKind)}
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              >
                {METRIC_KINDS.map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Description</label>
              <input
                type="text"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="Optional"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              />
            </div>
          </div>

          {formError && (
            <p className="t-small" style={{ color: "var(--fail)" }}>{formError}</p>
          )}

          <div className="flex items-center gap-2 pt-1">
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-1.5 t-small font-medium border transition-colors hover:opacity-90 disabled:opacity-40"
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
            >
              {submitting ? "Creating..." : "Create metric"}
            </button>
            <button
              type="button"
              onClick={() => { setFormOpen(false); setFormError(null); }}
              className="px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-1)" }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading && (
        <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
          <p className="t-small" style={{ color: "var(--fg-3)" }}>Loading metrics...</p>
        </div>
      )}

      {fetchError && (
        <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
          <p className="t-small" style={{ color: "var(--fail)" }}>{fetchError}</p>
        </div>
      )}

      {!loading && !fetchError && (
        <div className="border border-line" style={{ background: "var(--bg-1)" }}>
          {metrics.length === 0 ? (
            <div className="px-4 py-12 text-center t-small" style={{ color: "var(--fg-3)" }}>
              No metrics tracked yet. Connect a source and run checks to generate metrics.
            </div>
          ) : (
            <table className="w-full" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr className="border-b border-line">
                  {["", "Metric", "Dataset", "Kind", "Owners", "Last run", ""].map((h, i) => (
                    <th key={i} className="px-3 py-2 text-left t-micro"
                        style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.map((m) => (
                  <tr key={m.fqn} className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors">
                    <td className="px-3 py-2" style={{ width: 32 }}>
                      <VerdictDot verdict={m.current_verdict} />
                    </td>
                    <td className="px-3 py-2">
                      <Link href={`/metrics/${encodeURIComponent(m.fqn)}`}
                            className="t-small font-mono hover:underline"
                            style={{ color: "var(--accent)" }}>
                        {m.display_name}
                      </Link>
                      <p className="t-micro mt-0.5 font-mono" style={{ color: "var(--fg-3)" }}>{m.fqn}</p>
                    </td>
                    <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>{m.dataset}</td>
                    <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-2)" }}>{m.kind}</td>
                    <td className="px-3 py-2 t-small" style={{ color: "var(--fg-2)" }}>{m.owners.join(", ")}</td>
                    <td className="px-3 py-2 t-small" style={{ color: "var(--fg-3)" }}>{m.last_run ?? "--"}</td>
                    <td className="px-3 py-2 text-right" style={{ width: 100 }} onClick={(e) => e.stopPropagation()}>
                      {confirmDeleteFqn === m.fqn ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleDeleteMetric(m.fqn)}
                            disabled={deletingFqn}
                            className="flex items-center gap-1 px-2 py-0.5 t-micro border transition-colors"
                            style={{ borderColor: "var(--fail)", color: "var(--fail)", background: "rgba(224,123,110,0.08)" }}
                          >
                            {deletingFqn ? <Loader2 size={10} strokeWidth={2} className="animate-spin" /> : "delete"}
                          </button>
                          <button
                            onClick={() => setConfirmDeleteFqn(null)}
                            className="t-micro px-1 hover:opacity-60"
                            style={{ color: "var(--fg-3)" }}
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmDeleteFqn(m.fqn)}
                          className="inline-flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors ml-auto"
                          style={{ color: "var(--fg-3)" }}
                          title="Delete metric"
                        >
                          <Trash2 size={11} strokeWidth={1.6} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

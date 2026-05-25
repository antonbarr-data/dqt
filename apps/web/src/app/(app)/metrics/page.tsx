"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { ChevronDown, Loader2, Plus, Sparkles, Trash2, X } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface MetricSummary {
  fqn: string;
  display_name: string;
  kind: string;
  dataset: string;
  source_id: string | null;
  column_name: string | null;
  tags: string[];
  current_verdict: string | null;
  pinned: boolean;
}

interface DatasetItem {
  id: string;
  source: string;
  schema: string;
}

interface SuggestedMetric {
  name: string;
  definition: string;
  kind: string;
  grain: string | null;
  additivity: string | null;
  good_direction: string | null;
  cadence: string | null;
  dataset: string;
  display_name: string;
  source_column: string;
  confidence: number;
  reasoning: string;
}

function VerdictDot({ verdict }: { verdict: string | null }) {
  const color =
    verdict === "pass" ? "var(--pass)" :
    verdict === "fail" ? "var(--fail)" :
    verdict === "warn" ? "var(--warn)" : "var(--fg-3)";
  return (
    <span style={{ display: "inline-block", width: 8, height: 8, background: color, boxShadow: `0 0 0 2px ${color}28`, flexShrink: 0 }} />
  );
}

const METRIC_KINDS = ["ratio", "count", "sum", "model"] as const;
const KIND_HINT: Record<string, string> = {
  ratio: "fraction, rate, or average",
  count: "row or event count",
  sum: "summed total",
  model: "ML model output",
};

function KindFilterHeader({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (v: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative inline-flex items-center gap-1 select-none" style={{ userSelect: "none" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 t-micro hover:opacity-80"
        style={{ color: value ? "var(--accent)" : "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}
      >
        Kind
        {value && <span className="font-mono">: {value}</span>}
        <ChevronDown size={10} strokeWidth={2} style={{ opacity: 0.6 }} />
      </button>
      {value && (
        <button onClick={() => onChange(null)} className="hover:opacity-70">
          <X size={10} style={{ color: "var(--accent)" }} />
        </button>
      )}
      {open && (
        <div
          className="absolute top-full left-0 mt-1 border border-line z-50 py-1"
          style={{ background: "var(--bg-1)", minWidth: 100, boxShadow: "0 4px 12px rgba(0,0,0,0.3)" }}
        >
          {([null, ...METRIC_KINDS] as (string | null)[]).map((k) => (
            <button
              key={String(k)}
              onClick={() => { onChange(k); setOpen(false); }}
              className="w-full text-left px-3 py-1.5 t-small hover:bg-bg-2"
              style={{ color: value === k ? "var(--accent)" : "var(--fg-1)" }}
            >
              {k ?? "All"}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState<string | null>(null);
  const [confirmDeleteFqn, setConfirmDeleteFqn] = useState<string | null>(null);
  const [deletingFqn, setDeletingFqn] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formKind, setFormKind] = useState<"ratio" | "count" | "sum" | "model">("ratio");
  const [formDataset, setFormDataset] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [editingKindFqn, setEditingKindFqn] = useState<string | null>(null);

  // Suggest state
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestedMetric[]>([]);
  const [addedFqns, setAddedFqns] = useState<Set<string>>(new Set());
  const [addingName, setAddingName] = useState<string | null>(null);
  const [suggestError, setSuggestError] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/metrics`);
      if (res.ok) setMetrics(await res.json());
      else setFetchError("Failed to load metrics.");
    } catch {
      setFetchError("Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadMetrics(); }, [loadMetrics]);

  async function openSuggest() {
    setSuggestOpen(true);
    setSuggestions([]);
    setSuggestError(null);
    if (datasets.length === 0) {
      const res = await fetch(`${API}/api/v1/datasets`).catch(() => null);
      if (res?.ok) {
        const data: DatasetItem[] = await res.json();
        setDatasets(data);
        if (data.length > 0) setSelectedDataset(data[0].id);
      }
    }
  }

  async function runSuggest() {
    if (!selectedDataset) return;
    setSuggesting(true);
    setSuggestError(null);
    setSuggestions([]);
    try {
      const colsRes = await fetch(`${API}/api/v1/datasets/${encodeURIComponent(selectedDataset)}/columns`);
      if (!colsRes.ok) throw new Error("Could not fetch columns for this dataset");
      const cols: { name: string; data_type: string; nullable: boolean }[] = await colsRes.json();
      if (cols.length === 0) throw new Error("No columns found in this dataset");

      const dataset = datasets.find((d) => d.id === selectedDataset);
      const tableName = dataset?.id ?? selectedDataset;

      const sugRes = await fetch(`${API}/api/v1/metrics/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          columns: cols.map((c) => ({
            dataset: tableName,
            column: c.name,
            data_type: c.data_type,
            null_rate: 0.0,
          })),
        }),
      });
      if (!sugRes.ok) throw new Error("Suggestion failed");
      const result = await sugRes.json();
      if (!result.metrics || result.metrics.length === 0) {
        setSuggestError("No metric candidates found in this dataset. Try a fact or aggregation table.");
      } else {
        setSuggestions(result.metrics);
      }
    } catch (e: unknown) {
      setSuggestError(e instanceof Error ? e.message : "Failed to generate suggestions");
    } finally {
      setSuggesting(false);
    }
  }

  async function addSuggestion(s: SuggestedMetric) {
    setAddingName(s.name);
    try {
      const res = await fetch(`${API}/api/v1/metrics/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metrics: [{
            display_name: s.display_name || s.name,
            kind: s.kind || "ratio",
            dataset: s.dataset,
            description: s.definition || "",
            grain: s.grain || null,
            additivity: s.additivity || null,
            good_direction: s.good_direction || null,
            refresh_cadence: s.cadence || null,
          }],
        }),
      });
      if (res.ok) {
        setAddedFqns((prev) => new Set(Array.from(prev).concat(s.name)));
        await loadMetrics();
      }
    } finally {
      setAddingName(null);
    }
  }

  function handleDeleteMetric(fqn: string) {
    setDeletingFqn(true);
    fetch(`${API}/api/v1/metrics/${encodeURIComponent(fqn)}`, { method: "DELETE" })
      .then(() => setMetrics((prev) => prev.filter((m) => m.fqn !== fqn)))
      .catch(() => {})
      .finally(() => { setDeletingFqn(false); setConfirmDeleteFqn(null); });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formName.trim() || !formDataset.trim()) { setFormError("Name and dataset are required."); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      const res = await fetch(`${API}/api/v1/metrics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: formName.trim(), kind: formKind, dataset: formDataset.trim(), description: formDescription.trim() }),
      });
      if (res.status === 201) {
        setFormName(""); setFormKind("ratio"); setFormDataset(""); setFormDescription(""); setFormOpen(false);
        await loadMetrics();
      } else if (res.status === 409) {
        setFormError("A metric with this name already exists for that dataset.");
      } else {
        const err = await res.json().catch(() => ({}));
        setFormError(err.detail || "Failed to create metric.");
      }
    } catch { setFormError("Network error."); }
    finally { setSubmitting(false); }
  }

  async function handlePatchKind(fqn: string, kind: string) {
    await fetch(`${API}/api/v1/metrics/${encodeURIComponent(fqn)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind }),
    });
    setMetrics((prev) => prev.map((m) => m.fqn === fqn ? { ...m, kind } : m));
    setEditingKindFqn(null);
  }

  const filtered = kindFilter ? metrics.filter((m) => m.kind === kindFilter) : metrics;

  return (
    <div className="p-6 overflow-auto">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Metrics</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => suggestOpen ? setSuggestOpen(false) : openSuggest()}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80"
            style={{
              background: suggestOpen ? "rgba(99,102,241,0.1)" : "var(--bg-2)",
              color: suggestOpen ? "var(--accent)" : "var(--fg-1)",
              borderColor: suggestOpen ? "var(--accent)" : "var(--line)",
            }}
          >
            <Sparkles size={12} strokeWidth={1.8} />
            Suggest metrics
          </button>
          <button
            onClick={() => { setFormOpen((v) => !v); setFormError(null); }}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80"
            style={{
              background: formOpen ? "var(--accent-bg)" : "var(--bg-2)",
              color: formOpen ? "var(--accent)" : "var(--fg-0)",
              borderColor: formOpen ? "var(--accent)" : "var(--line)",
            }}
          >
            <Plus size={11} strokeWidth={1.6} />
            New metric
          </button>
        </div>
      </div>

      {/* Suggest panel */}
      {suggestOpen && (
        <div className="mb-6 border border-line" style={{ background: "var(--bg-1)" }}>
          <div className="px-4 py-3 border-b border-line flex items-center justify-between">
            <span className="t-small" style={{ color: "var(--fg-0)" }}>Suggest metrics from a dataset</span>
            <button onClick={() => setSuggestOpen(false)} className="hover:opacity-70">
              <X size={14} style={{ color: "var(--fg-3)" }} />
            </button>
          </div>
          <div className="p-4">
            {datasets.length === 0 && !suggesting && (
              <p className="t-small" style={{ color: "var(--fg-3)" }}>No datasets found. Connect a source first.</p>
            )}
            {datasets.length > 0 && suggestions.length === 0 && !suggesting && (
              <div className="flex items-center gap-3">
                <div>
                  <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Dataset</label>
                  <select
                    value={selectedDataset}
                    onChange={(e) => setSelectedDataset(e.target.value)}
                    className="px-2 py-1.5 t-small border border-line font-mono"
                    style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none", minWidth: 260 }}
                  >
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>{d.id}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={runSuggest}
                  disabled={!selectedDataset}
                  className="mt-5 flex items-center gap-1.5 px-4 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
                  style={{ color: "var(--accent)", borderColor: "var(--accent)" }}
                >
                  <Sparkles size={12} strokeWidth={1.8} />
                  Analyze
                </button>
              </div>
            )}
            {suggesting && (
              <div className="flex items-center gap-2 py-4">
                <Loader2 size={14} strokeWidth={2} className="animate-spin" style={{ color: "var(--accent)" }} />
                <span className="t-small" style={{ color: "var(--fg-2)" }}>Analyzing columns and generating suggestions…</span>
              </div>
            )}
            {suggestError && (
              <p className="t-small" style={{ color: "var(--fail)" }}>{suggestError}</p>
            )}
            {suggestions.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="t-small" style={{ color: "var(--fg-2)" }}>
                    <span style={{ color: "var(--fg-0)" }}>{suggestions.length}</span> suggestions for <span className="font-mono" style={{ color: "var(--fg-1)" }}>{selectedDataset}</span>
                  </p>
                  <button
                    onClick={() => { setSuggestions([]); setSuggestError(null); }}
                    className="t-micro border border-line px-2 py-0.5 hover:opacity-80"
                    style={{ color: "var(--fg-3)" }}
                  >
                    Try another dataset
                  </button>
                </div>
                <div className="divide-y divide-line border border-line">
                  {suggestions.map((s, i) => {
                    const added = addedFqns.has(s.name);
                    return (
                      <div key={i} className="px-4 py-3 flex items-start gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                            <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>
                              {s.display_name || s.name}
                            </span>
                            {s.kind && (
                              <span className="t-micro px-1.5 py-0.5 border border-line font-mono" style={{ color: "var(--fg-2)" }}>{s.kind}</span>
                            )}
                            {s.additivity && (
                              <span className="t-micro px-1.5 py-0.5 border border-line" style={{ color: "var(--fg-3)" }}>{s.additivity}</span>
                            )}
                            {s.good_direction && (
                              <span className="t-micro px-1.5 py-0.5 border border-line" style={{ color: s.good_direction === "up" ? "var(--pass)" : s.good_direction === "down" ? "var(--fail)" : "var(--warn)" }}>
                                {s.good_direction === "up" ? "↑ up" : s.good_direction === "down" ? "↓ down" : "⇔ in-band"}
                              </span>
                            )}
                          </div>
                          {s.definition && (
                            <p className="t-small" style={{ color: "var(--fg-2)" }}>{s.definition}</p>
                          )}
                          {s.reasoning && (
                            <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{s.reasoning}</p>
                          )}
                        </div>
                        <button
                          onClick={() => addSuggestion(s)}
                          disabled={added || addingName === s.name}
                          className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
                          style={{
                            color: added ? "var(--pass)" : "var(--accent)",
                            borderColor: added ? "var(--pass)" : "var(--accent)",
                          }}
                        >
                          {addingName === s.name ? (
                            <Loader2 size={11} strokeWidth={2} className="animate-spin" />
                          ) : added ? (
                            "Added ✓"
                          ) : (
                            <><Plus size={11} strokeWidth={2} /> Add</>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* New metric inline form */}
      {formOpen && (
        <form onSubmit={handleSubmit} className="mb-6 border border-line p-4 space-y-3" style={{ background: "var(--bg-1)" }}>
          <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>New metric</p>
          <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Name</label>
              <input
                type="text" value={formName} onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Conversion rate"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              />
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Dataset</label>
              <input
                type="text" value={formDataset} onChange={(e) => setFormDataset(e.target.value)}
                placeholder="e.g. fct_orders"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              />
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Kind</label>
              <select
                value={formKind} onChange={(e) => setFormKind(e.target.value as typeof formKind)}
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              >
                {METRIC_KINDS.map((k) => (<option key={k} value={k}>{k}</option>))}
              </select>
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Description</label>
              <input
                type="text" value={formDescription} onChange={(e) => setFormDescription(e.target.value)}
                placeholder="Optional"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              />
            </div>
          </div>
          {formError && <p className="t-small" style={{ color: "var(--fail)" }}>{formError}</p>}
          <div className="flex items-center gap-2 pt-1">
            <button
              type="submit" disabled={submitting}
              className="px-4 py-1.5 t-small font-medium border transition-colors hover:opacity-90 disabled:opacity-40"
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
            >
              {submitting ? "Creating..." : "Create metric"}
            </button>
            <button
              type="button" onClick={() => { setFormOpen(false); setFormError(null); }}
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
          {filtered.length === 0 ? (
            <div className="px-4 py-12 text-center t-small" style={{ color: "var(--fg-3)" }}>
              {kindFilter ? `No ${kindFilter} metrics.` : "No metrics tracked yet."}
            </div>
          ) : (
            <table className="w-full" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr className="border-b border-line">
                  <th className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, width: 32 }} />
                  <th className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>Metric</th>
                  <th className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>Path</th>
                  <th className="px-3 py-2 text-left" style={{ width: 130 }}>
                    <KindFilterHeader value={kindFilter} onChange={setKindFilter} />
                  </th>
                  <th className="px-3 py-2" style={{ width: 100 }} />
                </tr>
              </thead>
              <tbody>
                {filtered.map((m) => (
                  <tr key={m.fqn} className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors">
                    <td className="px-3 py-2" style={{ width: 32 }}>
                      <VerdictDot verdict={m.current_verdict} />
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        href={`/metrics/${encodeURIComponent(m.fqn)}`}
                        className="t-small font-mono hover:underline"
                        style={{ color: "var(--accent)" }}
                      >
                        {m.display_name}
                      </Link>
                      <p className="t-micro mt-0.5 font-mono" style={{ color: "var(--fg-3)" }}>{m.fqn}</p>
                    </td>
                    <td className="px-3 py-2">
                      <span className="t-micro font-mono" style={{ color: "var(--fg-2)" }}>
                        {[m.source_id, m.dataset, m.column_name].filter(Boolean).join(" / ") || m.dataset}
                      </span>
                    </td>
                    <td className="px-2 py-1.5" onClick={(e) => { e.stopPropagation(); setEditingKindFqn(m.fqn); }}>
                      {editingKindFqn === m.fqn ? (
                        <select
                          autoFocus defaultValue={m.kind}
                          onChange={(e) => handlePatchKind(m.fqn, e.target.value)}
                          onBlur={() => setEditingKindFqn(null)}
                          className="t-small font-mono border border-accent outline-none px-1 py-0.5"
                          style={{ background: "var(--bg-2)", color: "var(--accent)" }}
                        >
                          {METRIC_KINDS.map((k) => (
                            <option key={k} value={k} title={KIND_HINT[k]}>{k}</option>
                          ))}
                        </select>
                      ) : (
                        <span
                          className="t-small font-mono cursor-pointer hover:opacity-70"
                          style={{ color: "var(--fg-2)" }}
                          title={`${KIND_HINT[m.kind] ?? m.kind} — click to edit`}
                        >
                          {m.kind}
                        </span>
                      )}
                    </td>
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

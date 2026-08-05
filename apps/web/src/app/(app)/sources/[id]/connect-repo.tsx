"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, Loader2, GitBranch, Sparkles } from "lucide-react";
import { toast } from "sonner";

// ─── types (mirror the ImportProposal payload) ───────────────────────────────
interface Col {
  name: string;
  data_type: string | null;
  nullable: boolean | null;
  description: string | null;
  is_time: boolean;
  is_metric: boolean;
  primary_key: boolean;
  unique: boolean;
  available: boolean;
  live_data_type: string | null;
}
interface Metric {
  id: string;
  name: string;
  expression: string | null;
  kind: string;
  datatype: string | null;
  description: string | null;
  column_name: string | null;
}
interface Provenance { format: "okf" | "ossie"; path: string }
interface Dataset {
  id: string;
  schema_name: string;
  table: string;
  description: string | null;
  available: boolean;
  primary_key: string[];
  unique_keys: string[][];
  columns: Col[];
  metrics: Metric[];
  provenance: Provenance[];
}
interface Check {
  id: string;
  dataset: string;
  column_name: string | null;
  detector_slug: string;
  params: Record<string, unknown>;
  rationale: string;
  enabled: boolean;
}
interface Knowledge { id: string; title: string; kind: string; body: string; provenance: Provenance | null }
interface Payload {
  datasets: Dataset[];
  checks: Check[];
  knowledge: Knowledge[];
  conflicts: string[];
  sources_seen: string[];
}
interface RepoRow {
  id: string;
  git_url: string;
  branch: string | null;
  status: string;
  last_commit: string | null;
  last_synced_at: string | null;
}

const FORMAT_LABEL: Record<string, string> = { okf: "Google OKF", ossie: "Apache Ossie" };

function toggle<T>(set: Set<T>, key: T): Set<T> {
  const next = new Set(set);
  next.has(key) ? next.delete(key) : next.add(key);
  return next;
}

// ─── small inline badge ───────────────────────────────────────────────────────
function Tag({ text, tone = "muted" }: { text: string; tone?: "muted" | "accent" | "pass" | "fail" }) {
  const color =
    tone === "accent" ? "var(--accent)" :
    tone === "pass" ? "var(--pass)" :
    tone === "fail" ? "var(--fail)" : "var(--fg-2)";
  return (
    <span className="t-micro font-mono px-1.5 py-0.5 border" style={{ borderColor: color, color, background: "transparent", whiteSpace: "nowrap" }}>
      {text}
    </span>
  );
}

export function ConnectRepo({ sourceId }: { sourceId: string }) {
  const [gitUrl, setGitUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [subpath, setSubpath] = useState("");
  const [phase, setPhase] = useState<"idle" | "extracting" | "review" | "applying">("idle");
  const [proposalId, setProposalId] = useState<string | null>(null);
  const [payload, setPayload] = useState<Payload | null>(null);
  const [error, setError] = useState("");
  const [repos, setRepos] = useState<RepoRow[]>([]);

  const [selDs, setSelDs] = useState<Set<string>>(new Set());
  const [selMetric, setSelMetric] = useState<Set<string>>(new Set());
  const [selCheck, setSelCheck] = useState<Set<string>>(new Set());
  const [selKnow, setSelKnow] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const loadRepos = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/sources/${encodeURIComponent(sourceId)}/repos`);
      if (res.ok) setRepos(await res.json());
    } catch { /* ignore */ }
  }, [sourceId]);

  useEffect(() => { loadRepos(); }, [loadRepos]);

  const applyDefaults = useCallback((p: Payload) => {
    const ds = new Set<string>();
    const metrics = new Set<string>();
    for (const d of p.datasets) {
      if (!d.available) continue;
      ds.add(d.id);
      for (const m of d.metrics) metrics.add(m.id);
    }
    const checks = new Set<string>();
    for (const c of p.checks) if (ds.has(c.dataset)) checks.add(c.id);
    setSelDs(ds);
    setSelMetric(metrics);
    setSelCheck(checks);
    setSelKnow(new Set(p.knowledge.map((k) => k.id)));
    setExpanded(new Set(p.datasets.filter((d) => d.available).map((d) => d.id)));
  }, []);

  async function pollProposal(id: string) {
    for (let i = 0; i < 80; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      const res = await fetch(`/api/v1/proposals/${id}`);
      if (!res.ok) continue;
      const data = await res.json();
      if (data.status === "ready") {
        setPayload(data.payload as Payload);
        applyDefaults(data.payload as Payload);
        setPhase("review");
        return;
      }
      if (data.status === "failed") {
        setError(data.error || "Extraction failed");
        setPhase("idle");
        toast.error("Extraction failed");
        return;
      }
    }
    setError("Extraction timed out");
    setPhase("idle");
  }

  async function handleExtract() {
    if (!gitUrl.trim()) return;
    setError("");
    setPhase("extracting");
    try {
      const res = await fetch(`/api/v1/sources/${encodeURIComponent(sourceId)}/repos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ git_url: gitUrl.trim(), branch: branch.trim() || null, subpath: subpath.trim() || null }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.detail || "Could not start extraction");
        setPhase("idle");
        return;
      }
      const { proposal_id } = await res.json();
      setProposalId(proposal_id);
      await pollProposal(proposal_id);
      await loadRepos();
    } catch (e) {
      setError(String(e));
      setPhase("idle");
    }
  }

  async function handleSync(repoId: string) {
    setError("");
    setPhase("extracting");
    try {
      const res = await fetch(`/api/v1/repos/${encodeURIComponent(repoId)}/sync`, { method: "POST" });
      if (!res.ok) { setPhase("idle"); toast.error("Sync failed"); return; }
      const { proposal_id } = await res.json();
      setProposalId(proposal_id);
      await pollProposal(proposal_id);
    } catch (e) {
      setError(String(e));
      setPhase("idle");
    }
  }

  async function handleApply() {
    if (!proposalId) return;
    setPhase("applying");
    try {
      const res = await fetch(`/api/v1/proposals/${proposalId}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_ids: Array.from(selDs),
          metric_ids: Array.from(selMetric),
          check_ids: Array.from(selCheck),
          knowledge_ids: Array.from(selKnow),
        }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        toast.error(d.detail || "Import failed");
        setPhase("review");
        return;
      }
      const { created } = await res.json();
      toast.success(
        `Imported ${created.datasets} dataset(s), ${created.metrics} metric(s), ${created.checks} check(s), ${created.knowledge} note(s).`
      );
      resetToIdle();
      await loadRepos();
    } catch {
      toast.error("Import failed");
      setPhase("review");
    }
  }

  function resetToIdle() {
    setPhase("idle");
    setPayload(null);
    setProposalId(null);
    setGitUrl("");
    setBranch("");
    setSubpath("");
  }

  // ─── render: review tree ──────────────────────────────────────────────────
  if ((phase === "review" || phase === "applying") && payload) {
    const totalSel = selDs.size + selMetric.size + selCheck.size + selKnow.size;
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <p className="t-small" style={{ color: "var(--fg-2)" }}>
            Extracted from {payload.sources_seen.length} file(s). Select what to import.
          </p>
          <Tag text={`${totalSel} selected`} tone="accent" />
        </div>

        {payload.conflicts.length > 0 && (
          <div className="border px-3 py-2" style={{ borderColor: "var(--warn)", background: "transparent" }}>
            <p className="t-micro" style={{ color: "var(--warn)" }}>{payload.conflicts.length} conflict(s):</p>
            {payload.conflicts.slice(0, 5).map((c, i) => (
              <p key={i} className="t-micro font-mono" style={{ color: "var(--fg-2)" }}>{c}</p>
            ))}
          </div>
        )}

        <div className="border border-line" style={{ background: "var(--bg-1)", maxHeight: 420, overflowY: "auto" }}>
          {payload.datasets.map((d, di) => {
            const dsChecks = payload.checks.filter((c) => c.dataset === d.id);
            const isOpen = expanded.has(d.id);
            const fmt = d.provenance[0]?.format;
            return (
              <div key={d.id} className={di > 0 ? "border-t border-line" : ""}>
                <div className="flex items-center gap-2 px-3 py-2.5">
                  <input
                    type="checkbox"
                    checked={selDs.has(d.id)}
                    disabled={!d.available}
                    onChange={() => setSelDs((s) => toggle(s, d.id))}
                    style={{ accentColor: "var(--accent)", flexShrink: 0 }}
                  />
                  <button onClick={() => setExpanded((s) => toggle(s, d.id))} className="flex items-center gap-1.5 min-w-0" style={{ color: "var(--fg-0)" }}>
                    {isOpen ? <ChevronDown size={14} strokeWidth={1.6} /> : <ChevronRight size={14} strokeWidth={1.6} />}
                    <span className="t-small font-mono">{d.id}</span>
                  </button>
                  <div className="flex items-center gap-1.5 ml-auto">
                    {fmt && <Tag text={FORMAT_LABEL[fmt] ?? fmt} tone="muted" />}
                    {d.available ? <Tag text="in source" tone="pass" /> : <Tag text="not in source" tone="fail" />}
                  </div>
                </div>

                {isOpen && (
                  <div className="px-3 pb-3" style={{ paddingLeft: 32 }}>
                    {/* columns (informational) */}
                    <p className="t-micro uppercase mb-1" style={{ color: "var(--fg-3)" }}>Columns</p>
                    <div className="flex flex-col gap-1 mb-3">
                      {d.columns.map((c) => (
                        <div key={c.name} className="flex items-center gap-2">
                          <span className="t-small font-mono" style={{ color: c.available ? "var(--fg-0)" : "var(--fg-3)" }}>{c.name}</span>
                          <span className="t-micro" style={{ color: "var(--fg-2)" }}>{c.live_data_type || c.data_type || ""}</span>
                          {c.primary_key && <Tag text="pk" tone="accent" />}
                          {c.is_time && <Tag text="time" tone="accent" />}
                          {c.is_metric && <Tag text="metric" tone="accent" />}
                          {!c.available && <Tag text="not in source" tone="fail" />}
                        </div>
                      ))}
                    </div>

                    {d.metrics.length > 0 && (
                      <>
                        <p className="t-micro uppercase mb-1" style={{ color: "var(--fg-3)" }}>Metrics</p>
                        <div className="flex flex-col gap-1 mb-3">
                          {d.metrics.map((m) => (
                            <label key={m.id} className="flex items-start gap-2 cursor-pointer">
                              <input type="checkbox" checked={selMetric.has(m.id)} onChange={() => setSelMetric((s) => toggle(s, m.id))} style={{ accentColor: "var(--accent)", marginTop: 3, flexShrink: 0 }} />
                              <span className="min-w-0">
                                <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{m.name}</span>
                                <span className="ml-2 t-micro" style={{ color: "var(--accent)" }}>{m.kind}</span>
                                {m.expression && <span className="ml-2 t-micro font-mono" style={{ color: "var(--fg-2)" }}>{m.expression}</span>}
                              </span>
                            </label>
                          ))}
                        </div>
                      </>
                    )}

                    {dsChecks.length > 0 && (
                      <>
                        <p className="t-micro uppercase mb-1" style={{ color: "var(--fg-3)" }}>Checks (created disabled)</p>
                        <div className="flex flex-col gap-1">
                          {dsChecks.map((c) => (
                            <label key={c.id} className="flex items-start gap-2 cursor-pointer">
                              <input type="checkbox" checked={selCheck.has(c.id)} disabled={!d.available} onChange={() => setSelCheck((s) => toggle(s, c.id))} style={{ accentColor: "var(--accent)", marginTop: 3, flexShrink: 0 }} />
                              <span className="min-w-0">
                                <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{c.column_name && c.column_name !== "*" ? c.column_name : d.table}</span>
                                <span className="ml-2 t-micro" style={{ color: "var(--accent)" }}>{c.detector_slug}</span>
                                <span className="block t-micro" style={{ color: "var(--fg-2)" }}>{c.rationale}</span>
                              </span>
                            </label>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {payload.knowledge.length > 0 && (
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div className="px-3 py-2 border-b border-line">
              <p className="t-micro uppercase" style={{ color: "var(--fg-3)" }}>Knowledge (agent context)</p>
            </div>
            <div className="flex flex-col">
              {payload.knowledge.map((k, i) => (
                <label key={k.id} className={`flex items-start gap-2 px-3 py-2 cursor-pointer ${i > 0 ? "border-t border-line" : ""}`}>
                  <input type="checkbox" checked={selKnow.has(k.id)} onChange={() => setSelKnow((s) => toggle(s, k.id))} style={{ accentColor: "var(--accent)", marginTop: 3, flexShrink: 0 }} />
                  <span className="min-w-0">
                    <span className="t-small" style={{ color: "var(--fg-0)" }}>{k.title}</span>
                    <span className="ml-2 t-micro" style={{ color: "var(--accent)" }}>{k.kind}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={handleApply}
            disabled={phase === "applying" || totalSel === 0}
            className="flex items-center gap-2 px-4 py-2 t-small border transition-colors"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", opacity: totalSel === 0 ? 0.5 : 1 }}
          >
            {phase === "applying" && <Loader2 size={14} className="animate-spin" />}
            Import selected
          </button>
          <button onClick={resetToIdle} className="px-4 py-2 t-small border border-line transition-colors hover:bg-bg-2" style={{ color: "var(--fg-1)" }}>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // ─── render: input + existing repos ─────────────────────────────────────────
  const busy = phase === "extracting";
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <input
          value={gitUrl}
          onChange={(e) => setGitUrl(e.target.value)}
          placeholder="Git URL of a Google OKF / Apache Ossie repo"
          disabled={busy}
          className="w-full px-3 py-2 border t-body outline-none transition-colors"
          style={{ background: "var(--bg-1)", color: "var(--fg-0)", borderColor: "var(--line)" }}
        />
        <div className="flex gap-2">
          <input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="branch (optional)" disabled={busy}
            className="flex-1 px-3 py-2 border t-small outline-none" style={{ background: "var(--bg-1)", color: "var(--fg-0)", borderColor: "var(--line)" }} />
          <input value={subpath} onChange={(e) => setSubpath(e.target.value)} placeholder="subpath (optional)" disabled={busy}
            className="flex-1 px-3 py-2 border t-small outline-none" style={{ background: "var(--bg-1)", color: "var(--fg-0)", borderColor: "var(--line)" }} />
        </div>
        {error && <p className="t-small" style={{ color: "var(--fail)" }}>{error}</p>}
        <button
          onClick={handleExtract}
          disabled={busy || !gitUrl.trim()}
          className="flex items-center gap-2 self-start px-4 py-2 t-small border transition-colors"
          style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", opacity: !gitUrl.trim() ? 0.5 : 1 }}
        >
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} strokeWidth={1.6} />}
          {busy ? "Extracting…" : "Extract"}
        </button>
      </div>

      {repos.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="t-micro uppercase" style={{ color: "var(--fg-3)" }}>Connected repositories</p>
          {repos.map((r) => (
            <div key={r.id} className="flex items-center gap-2 px-3 py-2 border border-line" style={{ background: "var(--bg-1)" }}>
              <GitBranch size={13} strokeWidth={1.6} style={{ color: "var(--fg-2)" }} />
              <span className="t-small font-mono min-w-0 truncate" style={{ color: "var(--fg-0)" }}>{r.git_url}</span>
              <span className="ml-auto flex items-center gap-2">
                <Tag text={r.status} tone={r.status === "ready" || r.status === "synced" ? "pass" : r.status === "failed" ? "fail" : "muted"} />
                <button onClick={() => handleSync(r.id)} disabled={busy} className="px-2 py-1 t-micro border border-line transition-colors hover:bg-bg-2" style={{ color: "var(--fg-1)" }}>
                  Sync
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ReconciliationBar } from "./reconciliation-bar";
import { EvidenceTable } from "./evidence-table";
import { SeriesChart } from "./series-chart";
import { AuditDrawer } from "./audit-drawer";

interface LineageNode {
  id: string;
  kind: string;
  label: string;
}

interface LineageEdge {
  source: string;
  target: string;
  kind: string;
}

interface CheckRunItem {
  id: string;
  dataset_id: string;
  column: string;
  detector: string;
  score: number | null;
  verdict: string;
  message: string;
  ran_at: string | null;
  ran_at_ago: string;
}

interface IncidentItem {
  id: number;
  dataset_id: string;
  column: string;
  detector: string;
  severity: string;
  message: string;
  status: string;
  opened_ago: string;
}

interface DataIssue {
  detector_slug: string;
  verdict: string;
  contribution_low: number;
  contribution_high: number;
  plain_english: string;
}

interface BusinessDriver {
  cause: string;
  lag: number;
  p_value: number;
  evidence_strength: string;
  contribution_low: number;
  contribution_high: number;
}

interface RuledOutItem {
  fqn: string;
  reason: string;
}

interface StreamState {
  summary: string | null;
  primaryChannel: "data" | "business" | "mixed";
  dataContribution: [number, number];
  businessContribution: [number, number];
  dataIssues: DataIssue[];
  businessDrivers: BusinessDriver[];
  ruledOut: RuledOutItem[];
  done: boolean;
  error: string | null;
  loading: boolean;
}

const INITIAL_STATE: StreamState = {
  summary: null, primaryChannel: "mixed",
  dataContribution: [0, 0], businessContribution: [0, 0],
  dataIssues: [], businessDrivers: [], ruledOut: [],
  done: false, error: null, loading: false,
};

export function InsightClient({ fqn, metric }: { fqn: string; metric: { current_value: number | null } }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [state, setState] = useState<StreamState>(INITIAL_STATE);
  const [lookback, setLookback] = useState(() => {
    const lb = searchParams.get("lookback");
    const n = lb ? parseInt(lb, 10) : 7;
    return n > 0 ? n : 7;
  });
  const abortRef = useRef<AbortController | null>(null);

  const setLookbackAndUrl = useCallback((days: number) => {
    setLookback(days);
    const sp = new URLSearchParams(searchParams.toString());
    sp.set("lookback", String(days));
    router.replace(`?${sp.toString()}`, { scroll: false });
  }, [router, searchParams]);
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditSentenceId, setAuditSentenceId] = useState<string | null>(null);
  const [serverCitations, setServerCitations] = useState<Record<string, string[]>>({});
  const [lineageNodes, setLineageNodes] = useState<LineageNode[]>([]);
  const [lineageEdges, setLineageEdges] = useState<LineageEdge[]>([]);
  const [activeChecks, setActiveChecks] = useState<CheckRunItem[]>([]);
  const [recentIncidents, setRecentIncidents] = useState<IncidentItem[]>([]);

  // Derive dataset table name from fqn (format: source.schema.table.quality)
  const datasetTable = fqn.split(".")[2] ?? fqn;

  async function runExplain(days: number) {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({ ...INITIAL_STATE, loading: true });

    try {
      const resp = await fetch(`/api/v1/metrics/${encodeURIComponent(fqn)}/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lookback_days: days }),
        signal: ctrl.signal,
      });
      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            setState((prev) => applyEvent(prev, evt));
            if (evt.type === "done" && evt.citations) {
              setServerCitations(evt.citations as Record<string, string[]>);
            }
          } catch { /* malformed chunk */ }
        }
      }
    } catch (e: unknown) {
      if ((e as Error)?.name !== "AbortError") {
        setState((prev) => ({ ...prev, loading: false, error: String(e) }));
      }
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { runExplain(lookback); }, [fqn]);

  useEffect(() => {
    fetch(`/api/v1/lineage/graph?root=${encodeURIComponent(fqn)}&depth=1&direction=both`)
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then((g) => { setLineageNodes(g.nodes ?? []); setLineageEdges(g.edges ?? []); })
      .catch(() => {});
  }, [fqn]);

  useEffect(() => {
    fetch(`/api/v1/checks?dataset_id=${encodeURIComponent(datasetTable)}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((items: CheckRunItem[]) => setActiveChecks(items.slice(0, 10)))
      .catch(() => {});
  }, [datasetTable]);

  useEffect(() => {
    fetch("/api/v1/incidents?status=open")
      .then((r) => (r.ok ? r.json() : []))
      .then((items: IncidentItem[]) =>
        setRecentIncidents(
          items
            .filter((i) => !datasetTable || i.dataset_id?.includes(datasetTable))
            .slice(0, 5)
        )
      )
      .catch(() => {});
  }, [datasetTable]);

  const WINDOWS = [
    { label: "7d", days: 7 }, { label: "30d", days: 30 },
    { label: "MTD", days: new Date().getDate() },
    { label: "QTD", days: Math.floor((Date.now() - new Date(new Date().getFullYear(), Math.floor(new Date().getMonth() / 3) * 3, 1).getTime()) / 86400000) },
  ];

  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        {WINDOWS.map((w) => (
          <button
            key={w.label}
            onClick={() => { setLookbackAndUrl(w.days); runExplain(w.days); }}
            className="t-small px-2.5 py-1 border transition-colors"
            style={{
              borderColor: lookback === w.days ? "var(--accent)" : "var(--line)",
              color: lookback === w.days ? "var(--accent)" : "var(--fg-2)",
              background: lookback === w.days ? "var(--accent-bg)" : "transparent",
            }}
          >
            {w.label}
          </button>
        ))}
        <button
          onClick={() => runExplain(lookback)}
          className="t-small px-2.5 py-1 border border-line transition-colors hover:bg-bg-2 ml-auto"
          style={{ color: "var(--fg-2)" }}
          disabled={state.loading}
        >
          {state.loading ? "Analyzing..." : "Refresh"}
        </button>
      </div>

      <div className="border-l-2 p-4 mb-6" style={{ borderColor: "var(--accent)", background: "var(--bg-2)" }}>
        {state.loading && !state.summary && (
          <span className="t-small animate-pulse" style={{ color: "var(--fg-3)" }}>Analyzing movement...</span>
        )}
        {state.error && (
          <p className="t-small" style={{ color: "var(--fail)" }}>Error: {state.error}</p>
        )}
        {state.summary && (
          <p className="t-body" style={{ color: "var(--fg-0)", lineHeight: 1.7 }}>
            {state.summary.split(/\. /).map((sentence, i) => (
              <span
                key={i}
                onClick={() => { setAuditSentenceId(`s${i}`); setAuditOpen(true); }}
                className="cursor-pointer hover:bg-bg-2 transition-colors"
                title="Click to see evidence"
                style={{ borderBottom: "1px dotted var(--line)" }}
              >
                {sentence}{" "}
              </span>
            ))}
          </p>
        )}
      </div>

      {(state.summary || state.done) && (
        <ReconciliationBar
          dataContribution={state.dataContribution}
          businessContribution={state.businessContribution}
          primaryChannel={state.primaryChannel}
        />
      )}

      {(state.dataIssues.length > 0 || state.businessDrivers.length > 0) && (
        <EvidenceTable
          rows={[
            ...state.dataIssues.map((issue) => ({
              source: `check:${issue.detector_slug}`,
              signal_type: "failed_check",
              magnitude: (issue.contribution_low + issue.contribution_high) / 2,
              magnitude_low: issue.contribution_low,
              magnitude_high: issue.contribution_high,
              evidence_strength: issue.verdict === "fail" ? "strong" : "moderate",
              detail: { plain_english: issue.plain_english },
            })),
            ...state.businessDrivers.map((d) => ({
              source: `granger:${d.cause}`,
              signal_type: "causal_edge",
              magnitude: (d.contribution_low + d.contribution_high) / 2,
              magnitude_low: d.contribution_low,
              magnitude_high: d.contribution_high,
              evidence_strength: d.evidence_strength,
              detail: { p_value: d.p_value, lag: d.lag },
            })),
          ]}
        />
      )}

      {state.dataIssues.length > 0 && (
        <div className="mb-6">
          <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Data issues
          </p>
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            {state.dataIssues.map((issue, i) => (
              <div key={i} className="px-3 py-2 border-b border-line last:border-0 flex items-center justify-between">
                <div>
                  <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{issue.detector_slug}</span>
                  <span className="t-small ml-2" style={{ color: "var(--fg-2)" }}>{issue.plain_english}</span>
                </div>
                <span className="t-micro px-1.5 font-mono"
                      style={{ color: issue.verdict === "fail" ? "var(--fail)" : "var(--warn)",
                               background: issue.verdict === "fail" ? "var(--fail-bg)" : "rgba(217,181,102,0.1)" }}>
                  {issue.verdict}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {state.businessDrivers.length > 0 && (
        <div className="mb-6">
          <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Business drivers
          </p>
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            {state.businessDrivers.map((d, i) => (
              <div key={i} className="px-3 py-2 border-b border-line last:border-0 flex items-center justify-between">
                <div>
                  <span className="t-small font-mono" style={{ color: "var(--accent)" }}>{d.cause}</span>
                  <span className="t-micro ml-2 font-mono" style={{ color: "var(--fg-3)" }}>
                    lag {d.lag} · p={d.p_value.toFixed(3)}
                  </span>
                </div>
                <span className="t-micro font-mono"
                      style={{ color: d.evidence_strength === "strong" ? "var(--pass)" :
                               d.evidence_strength === "moderate" ? "var(--warn)" : "var(--fg-3)" }}>
                  {d.evidence_strength}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {state.ruledOut.length > 0 && (
        <details className="mb-6">
          <summary className="t-micro cursor-pointer" style={{ color: "var(--fg-3)" }}>
            {state.ruledOut.length} candidates examined and ruled out
          </summary>
          <div className="mt-2 border border-line" style={{ background: "var(--bg-1)" }}>
            {state.ruledOut.map((r, i) => (
              <div key={i} className="px-3 py-2 border-b border-line last:border-0 flex items-center justify-between">
                <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{r.fqn}</span>
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>{r.reason}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      <SeriesChart fqn={fqn} />

      {/* Lineage strip */}
      {lineageNodes.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <p className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Lineage
            </p>
            <Link
              href="/lineage"
              className="t-micro"
              style={{ color: "var(--accent)" }}
            >
              See full lineage →
            </Link>
          </div>
          <div className="border border-line p-3 overflow-x-auto" style={{ background: "var(--bg-1)" }}>
            <LineageStrip nodes={lineageNodes} edges={lineageEdges} rootId={fqn} />
          </div>
        </div>
      )}

      {/* Active checks */}
      {activeChecks.length > 0 && (
        <div className="mb-6">
          <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Active checks
          </p>
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            {activeChecks.map((c) => (
              <div key={c.id} className="px-3 py-2 border-b border-line last:border-0 flex items-center gap-3">
                <span
                  className="w-2 h-2 flex-shrink-0 rounded-full"
                  style={{
                    background: c.verdict === "fail" ? "var(--fail)" : c.verdict === "warn" ? "var(--warn)" : "var(--pass)",
                    boxShadow: `0 0 0 2px ${c.verdict === "fail" ? "rgba(224,123,110,0.2)" : c.verdict === "warn" ? "rgba(217,181,102,0.2)" : "rgba(127,179,148,0.2)"}`,
                  }}
                />
                <span className="t-small font-mono flex-1 truncate" style={{ color: "var(--fg-0)" }}>
                  {c.column} · {c.detector}
                </span>
                <MiniSparkline score={c.score} verdict={c.verdict} />
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>{c.ran_at_ago}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent incidents */}
      {recentIncidents.length > 0 && (
        <div className="mb-6">
          <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Recent incidents
          </p>
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            {recentIncidents.map((inc) => (
              <Link
                key={inc.id}
                href={`/incidents/${inc.id}`}
                className="flex items-center gap-3 px-3 py-2 border-b border-line last:border-0 hover:bg-bg-2 transition-colors"
              >
                <span
                  className="w-2 h-2 flex-shrink-0 rounded-full"
                  style={{
                    background: inc.severity === "fail" ? "var(--fail)" : "var(--warn)",
                    boxShadow: `0 0 0 2px ${inc.severity === "fail" ? "rgba(224,123,110,0.2)" : "rgba(217,181,102,0.2)"}`,
                  }}
                />
                <span className="t-small flex-1 truncate" style={{ color: "var(--fg-0)" }}>{inc.message}</span>
                <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{inc.opened_ago}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <AuditDrawer
        open={auditOpen}
        sentenceId={auditSentenceId}
        citations={serverCitations}
        onClose={() => setAuditOpen(false)}
      />
    </div>
  );
}

function LineageStrip({
  nodes,
  edges,
  rootId,
}: {
  nodes: LineageNode[];
  edges: LineageEdge[];
  rootId: string;
}) {
  const upstreamIds = new Set(edges.filter((e) => e.target === rootId).map((e) => e.source));
  const downstreamIds = new Set(edges.filter((e) => e.source === rootId).map((e) => e.target));

  const upstream = nodes.filter((n) => upstreamIds.has(n.id)).slice(0, 3);
  const root = nodes.find((n) => n.id === rootId);
  const downstream = nodes.filter((n) => downstreamIds.has(n.id)).slice(0, 3);

  const NodeChip = ({ node, dim }: { node: LineageNode; dim?: boolean }) => (
    <div
      className="px-2 py-1 border border-line t-micro font-mono whitespace-nowrap"
      style={{
        background: "var(--bg-0)",
        color: dim ? "var(--fg-3)" : "var(--fg-1)",
        maxWidth: 120,
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
      title={node.id}
    >
      {node.label || node.id.split(".").pop()}
    </div>
  );

  const Arrow = () => (
    <span className="t-micro px-1" style={{ color: "var(--fg-3)" }}>→</span>
  );

  return (
    <div className="flex items-center flex-wrap gap-1">
      {upstream.map((n) => (
        <span key={n.id} className="flex items-center gap-1">
          <NodeChip node={n} dim />
          <Arrow />
        </span>
      ))}
      {root && (
        <div
          className="px-2 py-1 border t-micro font-mono whitespace-nowrap"
          style={{
            borderColor: "var(--accent)",
            background: "var(--accent-bg)",
            color: "var(--accent)",
            maxWidth: 160,
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={root.id}
        >
          {root.label || root.id.split(".").pop()}
        </div>
      )}
      {downstream.map((n) => (
        <span key={n.id} className="flex items-center gap-1">
          <Arrow />
          <NodeChip node={n} dim />
        </span>
      ))}
    </div>
  );
}

function MiniSparkline({ score, verdict }: { score: number | null; verdict: string }) {
  const color = verdict === "fail" ? "var(--fail)" : verdict === "warn" ? "var(--warn)" : "var(--pass)";
  const h = score != null ? Math.max(2, Math.round(score * 18)) : 9;
  return (
    <svg width={32} height={18} style={{ flexShrink: 0 }}>
      <rect x={0} y={18 - h} width={32} height={h} fill={color} opacity={0.35} />
      <line x1={0} y1={18 - h} x2={32} y2={18 - h} stroke={color} strokeWidth={1} />
    </svg>
  );
}

function applyEvent(prev: StreamState, evt: Record<string, unknown>): StreamState {
  switch (evt.type) {
    case "start":
      return { ...prev, loading: true };
    case "summary":
      return { ...prev, loading: false,
               summary: evt.text as string,
               primaryChannel: evt.primary_channel as "data" | "business" | "mixed" };
    case "channel_a":
      return { ...prev, dataIssues: evt.issues as DataIssue[],
               dataContribution: evt.estimated_contribution as [number, number] };
    case "channel_b":
      return { ...prev, businessDrivers: evt.drivers as BusinessDriver[],
               businessContribution: evt.estimated_contribution as [number, number] };
    case "ruled_out":
      return { ...prev, ruledOut: evt.items as RuledOutItem[] };
    case "done":
      return { ...prev, done: true, loading: false };
    case "error":
      return { ...prev, error: evt.message as string, loading: false };
    default:
      return prev;
  }
}

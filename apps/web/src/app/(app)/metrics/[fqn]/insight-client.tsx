"use client";

import { useState, useEffect, useRef } from "react";
import { ReconciliationBar } from "./reconciliation-bar";

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
  const [state, setState] = useState<StreamState>(INITIAL_STATE);
  const [lookback, setLookback] = useState(7);
  const abortRef = useRef<AbortController | null>(null);

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
            onClick={() => { setLookback(w.days); runExplain(w.days); }}
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
          <p className="t-body" style={{ color: "var(--fg-0)", lineHeight: 1.7 }}>{state.summary}</p>
        )}
      </div>

      {(state.summary || state.done) && (
        <ReconciliationBar
          dataContribution={state.dataContribution}
          businessContribution={state.businessContribution}
          primaryChannel={state.primaryChannel}
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
    </div>
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

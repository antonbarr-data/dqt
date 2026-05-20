"use client";

import { useEffect, useState, useCallback } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { FeedItemCard } from "@/components/feed/feed-item-card";

interface CheckScore {
  id: string;
  dataset_id: string;
  column: string;
  detector_slug: string;
  score: number;
  verdict: string;
  ran_at: string;
}

interface ScoreData {
  platform_score: number | null;
  checks: CheckScore[];
}

interface FeedItem {
  item_id: string;
  metric_fqn: string;
  display_name: string;
  observed_change: number;
  significance: number;
  primary_channel: "data" | "business" | "mixed";
  summary_paragraph: string;
  estimated_data_contribution: [number, number];
  estimated_business_contribution: [number, number];
  evidence_chips: { label: string; display_value: string; direction: "up" | "down" | "flat" }[];
  reviewed: boolean;
}

type ChannelFilter = "all" | "data" | "business" | "mixed";

const EXCLUDED_KEY = "dqt_score_excluded";

function loadExcluded(): Set<string> {
  try {
    const raw = localStorage.getItem(EXCLUDED_KEY);
    if (raw) return new Set(JSON.parse(raw) as string[]);
  } catch {}
  return new Set();
}

function saveExcluded(excluded: Set<string>): void {
  localStorage.setItem(EXCLUDED_KEY, JSON.stringify(Array.from(excluded)));
}

function scoreColor(score: number | null): string {
  if (score === null) return "var(--fg-3)";
  if (score >= 80) return "var(--pass)";
  if (score >= 60) return "var(--warn)";
  return "var(--fail)";
}

function verdictColor(verdict: string): string {
  if (verdict === "pass") return "var(--pass)";
  if (verdict === "warn") return "var(--warn)";
  return "var(--fail)";
}

export default function OverviewPage() {
  const [scoreData, setScoreData] = useState<ScoreData | null>(null);
  const [excludedIds, setExcludedIds] = useState<Set<string>>(new Set());
  const [configOpen, setConfigOpen] = useState(false);

  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<ChannelFilter>("all");
  const [lookback, setLookback] = useState("24h");

  useEffect(() => {
    setExcludedIds(loadExcluded());
  }, []);

  useEffect(() => {
    fetch("/api/v1/score")
      .then(r => r.ok ? r.json() : null)
      .then((d: ScoreData | null) => setScoreData(d))
      .catch(() => setScoreData(null));
  }, []);

  const loadFeed = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`/api/v1/feed/today?lookback=${lookback}&limit=20`);
      if (resp.ok) setItems(await resp.json());
      else setItems([]);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [lookback]);

  useEffect(() => { loadFeed(); }, [loadFeed]);

  const markReviewed = useCallback(async (itemId: string) => {
    await fetch(`/api/v1/feed/items/${itemId}/reviewed`, { method: "POST" });
    setItems(prev => prev.filter(i => i.item_id !== itemId));
  }, []);

  const toggleCheck = (id: string) => {
    setExcludedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      saveExcluded(next);
      return next;
    });
  };

  const allChecks = scoreData?.checks ?? [];
  const includedChecks = allChecks.filter(c => !excludedIds.has(c.id));
  const computedScore = includedChecks.length > 0
    ? Math.round(includedChecks.reduce((s, c) => s + c.score, 0) / includedChecks.length)
    : null;

  const passCount = includedChecks.filter(c => c.verdict === "pass").length;
  const warnCount = includedChecks.filter(c => c.verdict === "warn").length;
  const failCount = includedChecks.filter(c => c.verdict === "fail").length;

  const visible = filter === "all" ? items : items.filter(i => i.primary_channel === filter);

  return (
    <div className="p-6 space-y-8 max-w-5xl">
      <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Overview</h1>

      {/* dqt Score card */}
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div className="px-5 py-4 flex items-start justify-between gap-6">
          <div className="flex items-end gap-6">
            {/* Score number */}
            <div>
              <p className="t-micro mb-1.5" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
                dqt Score
              </p>
              <div className="flex items-baseline gap-1.5">
                <span
                  style={{
                    fontSize: 42, lineHeight: 1, fontWeight: 300,
                    color: scoreColor(computedScore),
                    fontFamily: "var(--font-jetbrains-mono)",
                  }}
                >
                  {computedScore ?? "--"}
                </span>
                <span className="t-small" style={{ color: "var(--fg-3)" }}>/100</span>
              </div>
            </div>

            {/* Bar + breakdown */}
            {allChecks.length > 0 && (
              <div className="mb-1 flex flex-col gap-2">
                <div style={{ width: 180, height: 3, background: "var(--line)", position: "relative" }}>
                  {computedScore !== null && (
                    <div style={{
                      position: "absolute", top: 0, left: 0,
                      width: `${computedScore}%`, height: "100%",
                      background: scoreColor(computedScore),
                      transition: "width 0.3s ease",
                    }} />
                  )}
                </div>
                <div className="flex items-center gap-3 t-micro" style={{ fontFamily: "var(--font-jetbrains-mono)" }}>
                  <span style={{ color: "var(--pass)" }}>{passCount} pass</span>
                  <span style={{ color: "var(--warn)" }}>{warnCount} warn</span>
                  <span style={{ color: "var(--fail)" }}>{failCount} fail</span>
                  {excludedIds.size > 0 && (
                    <span style={{ color: "var(--fg-3)" }}>· {excludedIds.size} excluded</span>
                  )}
                </div>
              </div>
            )}

            {allChecks.length === 0 && (
              <p className="t-small mb-1" style={{ color: "var(--fg-3)" }}>
                No checks configured yet.
              </p>
            )}
          </div>

          {/* Configure toggle */}
          <button
            onClick={() => setConfigOpen(v => !v)}
            className="flex items-center gap-1.5 t-micro px-2.5 py-1 border transition-colors hover:border-line-3 shrink-0"
            style={{
              color: configOpen ? "var(--accent)" : "var(--fg-2)",
              borderColor: configOpen ? "var(--accent)" : "var(--line)",
              background: configOpen ? "var(--accent-bg)" : "var(--bg-2)",
            }}
          >
            Configure
            {configOpen
              ? <ChevronUp size={11} strokeWidth={1.6} />
              : <ChevronDown size={11} strokeWidth={1.6} />}
          </button>
        </div>

        {/* Configure panel */}
        {configOpen && (
          <div className="border-t border-line" style={{ maxHeight: 340, overflowY: "auto" }}>
            {allChecks.length === 0 ? (
              <div className="px-5 py-6 text-center t-small" style={{ color: "var(--fg-3)" }}>
                No checks found. Connect a source and add checks to datasets.
              </div>
            ) : (
              <table className="w-full" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr className="border-b border-line">
                    {["", "Dataset", "Column", "Detector", "Score", "Verdict"].map((h, i) => (
                      <th
                        key={i}
                        className="px-3 py-2 t-micro text-left"
                        style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...allChecks].sort((a, b) => a.score - b.score).map(c => {
                    const included = !excludedIds.has(c.id);
                    const fg = included ? verdictColor(c.verdict) : "var(--fg-3)";
                    return (
                      <tr
                        key={c.id}
                        className="border-b border-line last:border-0 cursor-pointer hover:bg-bg-2 transition-colors"
                        onClick={() => toggleCheck(c.id)}
                      >
                        <td className="px-3 py-2" style={{ width: 32 }}>
                          <div style={{
                            width: 13, height: 13,
                            border: `1.5px solid ${included ? "var(--accent)" : "var(--line-3)"}`,
                            background: included ? "var(--accent-bg)" : "transparent",
                            display: "flex", alignItems: "center", justifyContent: "center",
                          }}>
                            {included && <div style={{ width: 5, height: 5, background: "var(--accent)" }} />}
                          </div>
                        </td>
                        <td className="px-3 py-2 t-small font-mono" style={{ color: included ? "var(--fg-1)" : "var(--fg-3)" }}>
                          {c.dataset_id}
                        </td>
                        <td className="px-3 py-2 t-small font-mono" style={{ color: included ? "var(--fg-1)" : "var(--fg-3)" }}>
                          {c.column}
                        </td>
                        <td className="px-3 py-2 t-small font-mono" style={{ color: included ? "var(--fg-2)" : "var(--fg-3)" }}>
                          {c.detector_slug}
                        </td>
                        <td className="px-3 py-2 t-small text-right font-mono" style={{ color: fg }}>
                          {c.score}
                        </td>
                        <td className="px-3 py-2 t-micro font-mono" style={{ color: fg }}>
                          {c.verdict}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* Metric movements section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
            Metric Movements
          </p>
          <div className="flex items-center gap-3">
            <select
              value={lookback}
              onChange={e => setLookback(e.target.value)}
              className="t-small border border-line px-2 py-1"
              style={{ background: "var(--bg-1)", color: "var(--fg-1)" }}
            >
              <option value="24h">Last 24h</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
            </select>
            <button
              onClick={loadFeed}
              className="t-small px-3 py-1 border border-line hover:border-accent transition-colors"
              style={{ color: "var(--fg-1)", background: "var(--bg-1)" }}
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="flex gap-2 mb-4">
          {(["all", "data", "business", "mixed"] as ChannelFilter[]).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="t-micro px-2 py-1 border transition-colors"
              style={{
                borderColor: filter === f ? "var(--accent)" : "var(--line)",
                color: filter === f ? "var(--accent)" : "var(--fg-2)",
                background: filter === f ? "var(--accent-bg)" : "var(--bg-1)",
                letterSpacing: "0.06em",
              }}
            >
              {f === "all" ? "All" : f === "data" ? "Data issues" : f === "business" ? "Business shifts" : "Mixed"}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="border border-line p-4 h-32 animate-pulse"
                   style={{ background: "var(--bg-1)" }} />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <div className="border border-line p-12 text-center" style={{ background: "var(--bg-1)" }}>
            <p className="t-small" style={{ color: "var(--fg-3)" }}>
              No significant movements in the last {lookback}.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {visible.map(item => (
              <FeedItemCard
                key={item.item_id}
                {...item}
                onMarkReviewed={markReviewed}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { Check, Sparkles, ChevronRight } from "lucide-react";
import { clsx } from "clsx";

/* ───────────── mock data ───────────── */

interface MockCheck {
  id: string;
  group: string;
  dataset: string;
  column: string;
  check: string;
  score: number;
  verdict: Verdict;
}

const MOCK_CHECKS: MockCheck[] = [
  { id: "1", group: "basic", dataset: "marketing_campaigns", column: "spend_usd", check: "value_in_range", score: 0.0, verdict: "pass" },
  { id: "2", group: "basic", dataset: "gigler_transactions", column: "amount_usd", check: "value_in_range", score: 0.023, verdict: "warn" },
  { id: "3", group: "basic", dataset: "gigler_transactions", column: "platform_fee_usd", check: "null_fraction", score: 0.087, verdict: "fail" },
  { id: "4", group: "basic", dataset: "gig_vendor_stats", column: "total_profile_views", check: "null_fraction", score: 0.031, verdict: "warn" },
  { id: "5", group: "outliers", dataset: "gigler_transactions", column: "amount_usd", check: "mad_outlier_fraction", score: 0.008, verdict: "pass" },
  { id: "6", group: "outliers", dataset: "gig_vendor_stats", column: "click_through_rate", check: "adjusted_boxplot_fraction", score: 0.002, verdict: "pass" },
  { id: "7", group: "distribution", dataset: "gig_prices", column: "avg_price_usd", check: "ks2sample", score: 0.032, verdict: "pass" },
  { id: "8", group: "basic", dataset: "marketing_campaigns", column: "quality_score", check: "completeness", score: 0.94, verdict: "warn" },
];

const AI_SUGGESTIONS = [
  {
    id: "s1",
    title: "Row count SLA: gig_vendor_stats",
    reason: "Expected 500–2,000 rows/day based on historical pattern. No volume check exists.",
    yaml: `check: row_count_in_range\ntable: gig_vendor_stats\nparams:\n  date_col: date\n  min_rows: 500\n  max_rows: 2000`,
  },
  {
    id: "s2",
    title: "Null fraction: total_profile_views",
    reason: "Column has 3.1% nulls (tracking pixel outages). Suggested threshold: warn >1%, fail >5%.",
    yaml: `check: null_fraction\ntable: gig_vendor_stats\ncolumn: total_profile_views\n# warn >1%, fail >5% (default thresholds)`,
  },
  {
    id: "s3",
    title: "Value bounds: click_through_rate",
    reason: "CTR > 1.0 indicates a tracking bug. Flag any value outside [0, 1].",
    yaml: `check: value_in_range\ntable: gig_vendor_stats\ncolumn: click_through_rate\nparams:\n  min_val: 0.0\n  max_val: 1.0`,
  },
  {
    id: "s4",
    title: "Freshness SLA: marketing_campaigns",
    reason: "freshness_sla_hours=24 declared in semantic.yaml. No freshness check exists yet.",
    yaml: `check: freshness\ntable: marketing_campaigns\ncolumn: date\nparams:\n  max_age_hours: 24`,
  },
];

const TABS = ["Auto-baselined", "Distribution", "Time series", "Outliers", "Dependencies", "Schema", "Basic"] as const;
type Tab = typeof TABS[number];

const TAB_GROUP_MAP: Record<Tab, string | null> = {
  "Auto-baselined": null,
  "Distribution": "distribution",
  "Time series": "timeseries",
  "Outliers": "outliers",
  "Dependencies": "dependencies",
  "Schema": "schema",
  "Basic": "basic",
};

type Verdict = "pass" | "warn" | "fail";

function StatusDot({ verdict }: { verdict: Verdict }) {
  const color =
    verdict === "pass" ? "var(--pass)" : verdict === "warn" ? "var(--warn)" : "var(--fail)";
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        background: color,
        boxShadow: `0 0 0 2px ${color}28`,
        flexShrink: 0,
      }}
    />
  );
}

function YamlBlock({ code }: { code: string }) {
  return (
    <pre
      className="t-micro font-mono overflow-x-auto p-2.5"
      style={{
        background: "var(--bg-0)",
        color: "var(--fg-1)",
        border: "1px solid var(--line)",
        whiteSpace: "pre",
        lineHeight: 1.6,
      }}
    >
      {code}
    </pre>
  );
}

/* ───────────── right panel ───────────── */

function RightPanel({ selectedCheckId }: { selectedCheckId: string | null }) {
  const [accepted, setAccepted] = useState<Set<string>>(new Set());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [generatedYaml, setGeneratedYaml] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  function accept(id: string) {
    setAccepted((prev) => { const next = new Set(prev); next.add(id); return next; });
    setToastMsg("Check added to suite");
    setTimeout(() => setToastMsg(null), 2400);
  }

  function generate() {
    if (!prompt.trim()) return;
    setGenerating(true);
    setTimeout(() => {
      setGeneratedYaml(
        `check: custom_check\n# Generated from: "${prompt}"\ntable: <table>\ncolumn: <column>\nparams: {}`
      );
      setGenerating(false);
    }, 800);
  }

  if (selectedCheckId) {
    const chk = MOCK_CHECKS.find((c) => c.id === selectedCheckId);
    if (!chk) return null;
    return (
      <div className="p-4 space-y-3">
        <p className="t-h3" style={{ color: "var(--fg-0)" }}>{chk.check}</p>
        <p className="t-small font-mono" style={{ color: "var(--fg-1)" }}>
          {chk.dataset}.{chk.column}
        </p>
        <YamlBlock
          code={`check: ${chk.check}\ntable: ${chk.dataset}\ncolumn: ${chk.column}`}
        />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-5 overflow-y-auto h-full">
      {/* toast */}
      {toastMsg && (
        <div
          className="fixed bottom-5 right-5 px-4 py-2 t-small border border-line z-50"
          style={{ background: "var(--bg-1)", color: "var(--fg-0)" }}
        >
          <span style={{ color: "var(--pass)", marginRight: 6 }}>✓</span>
          {toastMsg}
        </div>
      )}

      {/* AI suggestions header */}
      <div className="flex items-center gap-2">
        <Sparkles size={13} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
        <span className="t-h3" style={{ color: "var(--fg-0)" }}>AI Suggestions</span>
      </div>

      {/* suggestion cards */}
      <div className="space-y-3">
        {AI_SUGGESTIONS.map((s) => {
          const isAccepted = accepted.has(s.id);
          const isEditing = editingId === s.id;
          return (
            <div
              key={s.id}
              className="border border-line p-3 space-y-2 transition-colors"
              style={{
                background: isAccepted ? "rgba(127,179,148,0.06)" : "var(--bg-1)",
                borderColor: isAccepted ? "var(--pass)" : "var(--line)",
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="t-small font-medium" style={{ color: isAccepted ? "var(--pass)" : "var(--fg-0)" }}>
                  {isAccepted && <Check size={11} strokeWidth={2.5} style={{ display: "inline", marginRight: 4 }} />}
                  {s.title}
                </p>
              </div>
              <p className="t-micro" style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>
                {s.reason}
              </p>
              {isEditing && <YamlBlock code={s.yaml} />}
              {!isEditing && !isAccepted && <YamlBlock code={s.yaml} />}
              {isAccepted && !isEditing && (
                <p className="t-micro" style={{ color: "var(--pass)" }}>Added to suite</p>
              )}
              {!isAccepted && (
                <div className="flex items-center gap-2 pt-0.5">
                  <button
                    onClick={() => accept(s.id)}
                    className="flex items-center gap-1 px-2.5 py-1 t-micro border transition-colors hover:opacity-90"
                    style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
                  >
                    Accept <ChevronRight size={10} strokeWidth={2} />
                  </button>
                  <button
                    onClick={() => setEditingId(isEditing ? null : s.id)}
                    className="px-2.5 py-1 t-micro border border-line transition-colors hover:bg-bg-2"
                    style={{ color: "var(--fg-1)" }}
                  >
                    Edit
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* plain-english authoring */}
      <div className="border-t border-line pt-5 space-y-3">
        <p className="t-h3" style={{ color: "var(--fg-0)" }}>Author a Check</p>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe a check in plain English..."
          rows={3}
          className="w-full px-3 py-2 border border-line t-small outline-none resize-none"
          style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
        />
        <button
          onClick={generate}
          disabled={generating || !prompt.trim()}
          className={clsx(
            "px-3 py-1.5 t-small border transition-colors",
            generating || !prompt.trim() ? "opacity-40 cursor-not-allowed" : "hover:opacity-90"
          )}
          style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
        >
          {generating ? "Generating..." : "Generate →"}
        </button>
        {generatedYaml && <YamlBlock code={generatedYaml} />}
      </div>
    </div>
  );
}

/* ───────────── main page ───────────── */

export default function TestsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Basic");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const groupFilter = TAB_GROUP_MAP[activeTab];
  const visibleChecks =
    groupFilter === null
      ? MOCK_CHECKS
      : MOCK_CHECKS.filter((c) => c.group === groupFilter);

  return (
    <div className="flex h-full" style={{ height: "calc(100vh - 44px)" }}>
      {/* left panel */}
      <div className="flex flex-col flex-1 border-r border-line overflow-hidden">
        {/* tab bar */}
        <div className="flex border-b border-line overflow-x-auto" style={{ flexShrink: 0 }}>
          {TABS.map((tab) => {
            const active = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => { setActiveTab(tab); setSelectedId(null); }}
                className="px-4 py-2.5 t-small whitespace-nowrap border-b-2 transition-colors"
                style={{
                  borderBottomColor: active ? "var(--accent)" : "transparent",
                  color: active ? "var(--fg-0)" : "var(--fg-2)",
                  background: active ? "var(--bg-1)" : "transparent",
                }}
              >
                {tab}
              </button>
            );
          })}
        </div>

        {/* check list */}
        <div className="flex-1 overflow-y-auto">
          {visibleChecks.length === 0 ? (
            <div className="px-4 py-8 t-small text-center" style={{ color: "var(--fg-2)" }}>
              No checks in this category
            </div>
          ) : (
            <table className="w-full" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr className="border-b border-line" style={{ background: "var(--bg-1)" }}>
                  {["", "Dataset.Column", "Check", "Score"].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-2 text-left t-micro"
                      style={{
                        color: "var(--fg-2)",
                        fontWeight: 400,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleChecks.map((chk) => {
                  const selected = selectedId === chk.id;
                  return (
                    <tr
                      key={chk.id}
                      onClick={() => setSelectedId(selected ? null : chk.id)}
                      className="border-b border-line last:border-0 cursor-pointer transition-colors"
                      style={{
                        background: selected ? "var(--bg-2)" : undefined,
                      }}
                      onMouseEnter={(e) => {
                        if (!selected)
                          (e.currentTarget as HTMLTableRowElement).style.background = "var(--bg-2)";
                      }}
                      onMouseLeave={(e) => {
                        if (!selected)
                          (e.currentTarget as HTMLTableRowElement).style.background = "";
                      }}
                    >
                      <td className="px-3 py-2 w-8">
                        <StatusDot verdict={chk.verdict as Verdict} />
                      </td>
                      <td className="px-3 py-2">
                        <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>
                          {chk.dataset}.{chk.column}
                        </span>
                      </td>
                      <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>
                        {chk.check}
                      </td>
                      <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>
                        {chk.score}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* right panel — 420px */}
      <div
        className="overflow-y-auto flex-shrink-0"
        style={{ width: 420, background: "var(--bg-1)" }}
      >
        <RightPanel selectedCheckId={selectedId} />
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";

interface TopValue {
  value: string;
  count: number;
  pct: number;
}

interface ColumnStats {
  kind: string;
  top_values: TopValue[] | null;
  total_count: number | null;
}

function fmtNum(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toLocaleString();
}

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

// Simple pattern detection for string columns
function detectPattern(value: string): string | null {
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return "date";
  if (/^\d+(\.\d+)?$/.test(value)) return "numeric";
  if (/^[a-f0-9]{8}-[a-f0-9]{4}-/.test(value.toLowerCase())) return "uuid";
  if (/^[a-z]{2,3}$/.test(value.toLowerCase())) return "code";
  if (value.length > 50) return "long text";
  return null;
}

function PatternBadge({ pattern }: { pattern: string }) {
  const colors: Record<string, string> = {
    date: "var(--accent)",
    numeric: "var(--pass)",
    uuid: "#9b8fff",
    code: "var(--warn)",
    "long text": "var(--fg-3)",
  };
  return (
    <span className="t-micro px-1.5 py-0.5" style={{
      background: "var(--bg-2)", color: colors[pattern] ?? "var(--fg-3)",
      border: "1px solid var(--line)", fontFamily: "var(--font-jetbrains-mono)",
    }}>
      {pattern}
    </span>
  );
}

export function TopValuesPanel({ stats }: { stats: ColumnStats | null }) {
  const [tab, setTab] = useState<"values" | "patterns">("values");

  if (!stats || !stats.top_values || stats.top_values.length === 0) {
    return (
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div className="px-4 py-2.5 border-b border-line">
          <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Top values</span>
        </div>
        <div className="px-4 py-8 t-small flex items-center justify-center" style={{ color: "var(--fg-3)" }}>
          No value data
        </div>
      </div>
    );
  }

  const topValues = stats.top_values;
  const maxPct = Math.max(...topValues.map(v => v.pct), 0.001);

  // Pattern frequency (only for categorical)
  const patternMap: Record<string, number> = {};
  if (stats.kind === "categorical") {
    for (const tv of topValues) {
      const p = detectPattern(tv.value) ?? "other";
      patternMap[p] = (patternMap[p] ?? 0) + tv.count;
    }
  }
  const patterns = Object.entries(patternMap).sort((a, b) => b[1] - a[1]);
  const totalPatternCount = patterns.reduce((s, [, c]) => s + c, 0);

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Top values</span>
        {stats.kind === "categorical" && (
          <div className="flex items-center gap-0.5">
            {(["values", "patterns"] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="t-micro px-2 py-0.5"
                style={{
                  background: tab === t ? "var(--bg-2)" : "none",
                  border: tab === t ? "1px solid var(--line)" : "1px solid transparent",
                  color: tab === t ? "var(--fg-1)" : "var(--fg-3)",
                  cursor: "pointer",
                }}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      {tab === "values" ? (
        <div>
          {topValues.map((tv, i) => (
            <div key={i} className="px-4 py-2 border-b border-line last:border-0">
              <div className="flex items-center justify-between mb-1">
                <span
                  className="t-small font-mono truncate"
                  style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", maxWidth: "65%" }}
                  title={tv.value}
                >
                  {tv.value === "" ? <em style={{ color: "var(--fg-3)" }}>(empty)</em> : tv.value}
                </span>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="t-micro font-mono" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
                    {fmtNum(tv.count)}
                  </span>
                  <span className="t-micro font-mono" style={{ color: "var(--fg-1)", minWidth: 42, textAlign: "right", fontFamily: "var(--font-jetbrains-mono)" }}>
                    {fmtPct(tv.pct)}
                  </span>
                </div>
              </div>
              {/* Frequency bar */}
              <div style={{ height: 2, background: "var(--bg-2)", borderRadius: 1 }}>
                <div style={{
                  height: "100%", width: `${(tv.pct / maxPct) * 100}%`,
                  background: "var(--accent)", opacity: 0.7,
                }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div>
          {patterns.length === 0 ? (
            <div className="px-4 py-4 t-small" style={{ color: "var(--fg-3)" }}>No patterns detected</div>
          ) : (
            patterns.map(([pattern, count]) => {
              const pct = totalPatternCount > 0 ? count / totalPatternCount : 0;
              return (
                <div key={pattern} className="px-4 py-2.5 border-b border-line last:border-0">
                  <div className="flex items-center justify-between mb-1">
                    <PatternBadge pattern={pattern} />
                    <div className="flex items-center gap-2">
                      <span className="t-micro font-mono" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
                        {fmtNum(count)}
                      </span>
                      <span className="t-micro font-mono" style={{ color: "var(--fg-1)", minWidth: 42, textAlign: "right", fontFamily: "var(--font-jetbrains-mono)" }}>
                        {fmtPct(pct)}
                      </span>
                    </div>
                  </div>
                  <div style={{ height: 2, background: "var(--bg-2)", borderRadius: 1 }}>
                    <div style={{
                      height: "100%", width: `${pct * 100}%`,
                      background: "var(--accent)", opacity: 0.6,
                    }} />
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useState } from "react";

interface EvidenceRow {
  source: string;
  signal_type: string;
  magnitude: number;
  magnitude_low: number;
  magnitude_high: number;
  evidence_strength: string;
  detail?: Record<string, unknown>;
}

export function EvidenceTable({ rows }: { rows: EvidenceRow[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  if (!rows.length) return null;

  return (
    <div className="mb-6">
      <p
        className="t-micro mb-2"
        style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
      >
        Evidence considered
      </p>
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr className="border-b border-line">
              {["Source", "Type", "Contribution", "Strength"].map((h) => (
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
              <th className="px-3 py-2" style={{ width: 32 }} />
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <React.Fragment key={i}>
                <tr
                  className="border-b border-line last:border-0 cursor-pointer transition-colors"
                  style={{ background: "transparent" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-2)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  onClick={() => setExpanded(expanded === i ? null : i)}
                >
                  <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-0)" }}>
                    {row.source}
                  </td>
                  <td className="px-3 py-2 t-small" style={{ color: "var(--fg-2)" }}>
                    {row.signal_type}
                  </td>
                  <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>
                    {Math.round(row.magnitude_low * 100)}-{Math.round(row.magnitude_high * 100)}%
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className="t-micro font-mono"
                      style={{
                        color:
                          row.evidence_strength === "strong"
                            ? "var(--pass)"
                            : row.evidence_strength === "moderate"
                              ? "var(--warn)"
                              : "var(--fg-3)",
                      }}
                    >
                      {row.evidence_strength}
                    </span>
                  </td>
                  <td className="px-3 py-2 t-small text-right" style={{ color: "var(--fg-3)" }}>
                    {expanded === i ? "▲" : "▼"}
                  </td>
                </tr>
                {expanded === i && row.detail && (
                  <tr className="border-b border-line">
                    <td colSpan={5} className="px-3 py-2" style={{ background: "var(--bg-2)" }}>
                      <pre
                        className="t-micro font-mono"
                        style={{ color: "var(--fg-2)", whiteSpace: "pre-wrap" }}
                      >
                        {JSON.stringify(row.detail, null, 2)}
                      </pre>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

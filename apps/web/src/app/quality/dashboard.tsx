"use client";

import { useState, useMemo } from "react";
import type { DetectorRow } from "./page";

const fmt = (v: number | null) => (v == null ? "-" : v.toFixed(3));
const pct = (v: number | null) => (v == null ? 0 : Math.round(v * 100));

function barColor(v: number) {
  if (v >= 0.85) return "var(--pass)";
  if (v >= 0.70) return "var(--warn)";
  return "var(--fail)";
}

const FAMILY_STYLES: Record<string, { border: string; color: string }> = {
  drift:        { border: "#3a5a8a", color: "#7aa8d8" },
  outlier:      { border: "#5a3a6a", color: "#b87ad8" },
  timeseries:   { border: "#2a5a4a", color: "#7ad8b8" },
  distribution: { border: "#5a4a2a", color: "#d8b87a" },
  rule:         { border: "#4a4a2a", color: "#c8c87a" },
  baseline:     { border: "var(--line)", color: "var(--fg-2)" },
};

type SortCol = "slug" | "family" | "f1" | "precision" | "recall" | "fpr" | "n";

export function QualityDashboard({ rows }: { rows: DetectorRow[] }) {
  const [sortCol, setSortCol] = useState<SortCol>("f1");
  const [sortAsc, setSortAsc] = useState(false);
  const [familyFilter, setFamilyFilter] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [hideBaselines, setHideBaselines] = useState(true);

  const nonBase = rows.filter((r) => r.family !== "baseline");
  const best = nonBase.reduce((a, b) => (b.f1 > a.f1 ? b : a), nonBase[0] ?? { slug: "-", f1: 0 });
  const avgF1 = nonBase.length ? nonBase.reduce((s, r) => s + r.f1, 0) / nonBase.length : 0;
  const avgPrec = nonBase.filter((r) => r.precision != null);
  const avgPrecVal = avgPrec.length ? avgPrec.reduce((s, r) => s + r.precision!, 0) / avgPrec.length : 0;

  const families = useMemo(
    () => Array.from(new Set(rows.map((r) => r.family))).sort(),
    [rows]
  );

  const sorted = useMemo(() => {
    let filtered = [...rows];
    if (hideBaselines) filtered = filtered.filter((r) => r.family !== "baseline");
    if (familyFilter) filtered = filtered.filter((r) => r.family === familyFilter);
    if (searchQ) filtered = filtered.filter((r) => r.slug.includes(searchQ));
    filtered.sort((a, b) => {
      const av = a[sortCol] ?? -Infinity;
      const bv = b[sortCol] ?? -Infinity;
      if (typeof av === "string" && typeof bv === "string") {
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return filtered;
  }, [rows, sortCol, sortAsc, familyFilter, searchQ, hideBaselines]);

  function handleSort(col: SortCol) {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(false); }
  }

  function Th({ col, label, num }: { col: SortCol; label: string; num?: boolean }) {
    const active = sortCol === col;
    return (
      <th
        onClick={() => handleSort(col)}
        style={{
          textAlign: num ? "right" : "left",
          padding: "8px 12px",
          fontSize: 10,
          fontWeight: 500,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: active ? "var(--accent)" : "var(--fg-2)",
          fontFamily: "var(--font-jetbrains-mono)",
          cursor: "pointer",
          userSelect: "none",
          whiteSpace: "nowrap",
          borderBottom: "1px solid var(--line)",
        }}
      >
        {label}{active ? (sortAsc ? " ^" : " v") : ""}
      </th>
    );
  }

  const kpis = [
    { label: "detectors", value: nonBase.length.toString(), cls: "" },
    { label: "best f1", value: `${best.f1.toFixed(3)} (${best.slug})`, cls: best.f1 >= 0.9 ? "pass" : "warn" },
    { label: "avg f1", value: avgF1.toFixed(3), cls: avgF1 >= 0.75 ? "pass" : "warn" },
    { label: "avg precision", value: avgPrecVal.toFixed(3), cls: avgPrecVal >= 0.85 ? "pass" : "warn" },
  ] as const;

  return (
    <div style={{ background: "var(--bg-0)", minHeight: "100vh", color: "var(--fg-0)", fontFamily: "var(--font-inter-tight)" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 24px 80px" }}>

        {/* header */}
        <div style={{ borderBottom: "1px solid var(--line)", paddingBottom: 24, marginBottom: 32 }}>
          <h1 style={{ fontSize: 20, fontWeight: 300, letterSpacing: "-0.03em", fontFamily: "var(--font-jetbrains-mono)" }}>
            <span style={{ color: "var(--accent)" }}>dqt</span> / quality
          </h1>
          <p style={{ marginTop: 8, fontSize: 12, color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)" }}>
            Per-detector F1 on synthetic warehouse shapes, NAB subset, and Yahoo Webscope S5 subset.{" "}
            <a href="https://github.com/dqt-dev/dqt/blob/main/examples/benchmarks/results.csv" style={{ color: "var(--fg-1)", textDecoration: "none" }}>
              results.csv
            </a>
            {" "}·{" "}
            <a href="https://dqt.dev/docs/algorithms/" style={{ color: "var(--fg-1)", textDecoration: "none" }}>
              algorithm docs
            </a>
          </p>
        </div>

        {/* notice */}
        <div style={{
          background: "var(--bg-1)", border: "1px solid var(--line)", borderLeft: "3px solid var(--accent)",
          padding: "10px 14px", fontSize: 12, color: "var(--fg-1)", marginBottom: 24,
          fontFamily: "var(--font-jetbrains-mono)",
        }}>
          Updated automatically on each PyPI release. Every row is averaged over all benchmark datasets.
        </div>

        {/* KPI band */}
        <div style={{ display: "flex", gap: 24, marginBottom: 28, flexWrap: "wrap" }}>
          {kpis.map((k) => (
            <div key={k.label} style={{ background: "var(--bg-1)", border: "1px solid var(--line)", padding: "14px 18px", minWidth: 140 }}>
              <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.16em", color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)", marginBottom: 6 }}>
                {k.label}
              </div>
              <div style={{
                fontSize: 24, fontWeight: 300, letterSpacing: "-0.02em",
                fontFamily: "var(--font-jetbrains-mono)", fontVariantNumeric: "tabular-nums",
                color: k.cls === "pass" ? "var(--pass)" : k.cls === "warn" ? "var(--warn)" : "var(--fg-0)",
              }}>
                {k.value}
              </div>
            </div>
          ))}
        </div>

        {/* controls */}
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 20, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--fg-2)" }}>family</label>
            <select
              value={familyFilter}
              onChange={(e) => setFamilyFilter(e.target.value)}
              style={{ background: "var(--bg-1)", border: "1px solid var(--line)", color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, padding: "5px 10px", outline: "none" }}
            >
              <option value="">all</option>
              {families.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--fg-2)" }}>search</label>
            <input
              type="text"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value.trim())}
              placeholder="detector slug..."
              style={{ background: "var(--bg-1)", border: "1px solid var(--line)", color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, padding: "5px 10px", outline: "none", width: 200 }}
            />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--fg-1)", cursor: "pointer" }}>
            <input type="checkbox" checked={hideBaselines} onChange={(e) => setHideBaselines(e.target.checked)} />
            hide baselines
          </label>
        </div>

        {/* table */}
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr>
              <Th col="slug" label="Detector" />
              <Th col="family" label="Family" />
              <Th col="f1" label="F1" num />
              <Th col="precision" label="Precision" num />
              <Th col="recall" label="Recall" num />
              <Th col="n" label="N" num />
              <th style={{ width: 140, padding: "8px 12px", borderBottom: "1px solid var(--line)" }} />
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const fs = FAMILY_STYLES[r.family] ?? FAMILY_STYLES.rule;
              return (
                <tr
                  key={r.slug}
                  style={{ borderBottom: "1px solid var(--line)", opacity: r.family === "baseline" ? 0.5 : 1 }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-1)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                >
                  <td style={{ padding: "8px 12px", fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>
                    <a
                      href={`https://dqt.dev/docs/algorithms/${r.slug}`}
                      style={{ color: "var(--fg-1)", textDecoration: "none" }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "var(--fg-1)")}
                    >
                      {r.slug}
                    </a>
                  </td>
                  <td style={{ padding: "8px 12px" }}>
                    <span style={{
                      display: "inline-block", fontFamily: "var(--font-jetbrains-mono)", fontSize: 10,
                      padding: "2px 6px", border: `1px solid ${fs.border}`, color: fs.color,
                      textTransform: "uppercase", letterSpacing: "0.08em",
                    }}>
                      {r.family}
                    </span>
                  </td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>
                    {fmt(r.f1)}
                  </td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>
                    {fmt(r.precision)}
                  </td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>
                    {fmt(r.recall)}
                  </td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-2)" }}>
                    {r.n}
                  </td>
                  <td style={{ padding: "8px 12px", width: 140 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ flex: 1, height: 4, background: "var(--bg-2)", position: "relative", overflow: "hidden" }}>
                        <div style={{ height: "100%", width: `${pct(r.f1)}%`, background: barColor(r.f1), transition: "width 0.24s ease-out" }} />
                      </div>
                      <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, minWidth: 36, textAlign: "right", color: barColor(r.f1) }}>
                        {pct(r.f1)}%
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* footer */}
        <div style={{ marginTop: 48, borderTop: "1px solid var(--line)", paddingTop: 20, fontSize: 11, color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)" }}>
          Benchmark: synthetic warehouse shapes (lognormal / normal / Poisson / Beta), NAB subset, Yahoo Webscope S5 subset.{" "}
          Source:{" "}
          <a href="https://github.com/dqt-dev/dqt/tree/main/examples/benchmarks" style={{ color: "var(--fg-1)", textDecoration: "none" }}>
            examples/benchmarks/
          </a>
          . License: MIT.
        </div>
      </div>
    </div>
  );
}

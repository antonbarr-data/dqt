"use client";

import { useEffect, useState } from "react";

interface CausalEdge {
  cause: string;
  effect: string;
  direction: "upstream" | "downstream";
  p_value: number;
  evidence_strength: number;
  shap_attribution: number;
  lag: number;
}

const NODE_W = 130;
const NODE_H = 36;
const ROW_GAP = 54;
const SVG_W = 580;

function shortLabel(fqn: string): string {
  const parts = fqn.split(".");
  return parts[parts.length - 1] ?? fqn;
}

function strengthColor(s: number): string {
  return s > 0.7 ? "var(--pass)" : s > 0.4 ? "var(--warn)" : "var(--fg-3)";
}

export function CausalGraph({ fqn }: { fqn: string }) {
  const [edges, setEdges] = useState<CausalEdge[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/v1/metrics/${encodeURIComponent(fqn)}/causal-edges`)
      .then((r) => (r.ok ? r.json() : []))
      .then((d: CausalEdge[]) => { setEdges(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [fqn]);

  if (loading)
    return (
      <div className="h-16 flex items-center justify-center border border-line" style={{ background: "var(--bg-1)" }}>
        <span className="t-micro" style={{ color: "var(--fg-3)" }}>Loading causality...</span>
      </div>
    );

  if (!edges.length)
    return (
      <div className="h-16 flex items-center justify-center border border-line" style={{ background: "var(--bg-1)" }}>
        <span className="t-micro" style={{ color: "var(--fg-3)" }}>No causal edges discovered yet.</span>
      </div>
    );

  const upstream = edges.filter((e) => e.direction === "upstream");
  const downstream = edges.filter((e) => e.direction === "downstream");
  const maxRows = Math.max(upstream.length, downstream.length, 1);
  const svgH = Math.max(100, maxRows * ROW_GAP + 40);
  const cx = SVG_W / 2;
  const cy = svgH / 2;

  const upPos = upstream.map((_, i) => ({
    x: 10,
    y: (svgH / (upstream.length + 1)) * (i + 1) - NODE_H / 2,
  }));
  const downPos = downstream.map((_, i) => ({
    x: SVG_W - NODE_W - 10,
    y: (svgH / (downstream.length + 1)) * (i + 1) - NODE_H / 2,
  }));

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${SVG_W} ${svgH}`}
      style={{ overflow: "visible", display: "block" }}
    >
      <defs>
        <marker id="cg-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill="var(--fg-3)" />
        </marker>
        <marker id="cg-arrow-strong" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill="var(--accent)" />
        </marker>
      </defs>

      {/* Upstream nodes + edges */}
      {upstream.map((e, i) => {
        const { x, y } = upPos[i];
        const x1 = x + NODE_W;
        const y1 = y + NODE_H / 2;
        const x2 = cx - NODE_W / 2;
        const y2 = cy;
        const cpx = (x1 + x2) / 2;
        const strong = e.evidence_strength > 0.6;
        return (
          <g key={`up-${i}`}>
            <path
              d={`M${x1},${y1} C${cpx},${y1} ${cpx},${y2} ${x2},${y2}`}
              fill="none"
              stroke={strong ? "var(--accent)" : "var(--line)"}
              strokeWidth={strong ? 1.5 : 1}
              markerEnd={`url(#${strong ? "cg-arrow-strong" : "cg-arrow"})`}
              opacity={0.75}
            />
            <rect x={x} y={y} width={NODE_W} height={NODE_H} fill="var(--bg-2)" stroke="var(--line)" strokeWidth={1} />
            <text
              x={x + NODE_W / 2}
              y={y + NODE_H / 2 + 4}
              textAnchor="middle"
              style={{ fontSize: 10, fill: "var(--fg-1)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {shortLabel(e.cause)}
            </text>
            <text
              x={x + NODE_W + 5}
              y={y1 - 5}
              style={{ fontSize: 9, fill: strengthColor(e.evidence_strength) }}
            >
              lag {e.lag}
            </text>
          </g>
        );
      })}

      {/* Focal node */}
      <rect
        x={cx - NODE_W / 2}
        y={cy - NODE_H / 2}
        width={NODE_W}
        height={NODE_H}
        fill="var(--accent-bg)"
        stroke="var(--accent)"
        strokeWidth={1.5}
      />
      <text
        x={cx}
        y={cy + 5}
        textAnchor="middle"
        style={{ fontSize: 10, fill: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}
      >
        {shortLabel(fqn)}
      </text>

      {/* Downstream nodes + edges */}
      {downstream.map((e, i) => {
        const { x, y } = downPos[i];
        const x1 = cx + NODE_W / 2;
        const y1 = cy;
        const x2 = x;
        const y2 = y + NODE_H / 2;
        const cpx = (x1 + x2) / 2;
        const strong = e.evidence_strength > 0.6;
        return (
          <g key={`down-${i}`}>
            <path
              d={`M${x1},${y1} C${cpx},${y1} ${cpx},${y2} ${x2},${y2}`}
              fill="none"
              stroke={strong ? "var(--accent)" : "var(--line)"}
              strokeWidth={strong ? 1.5 : 1}
              markerEnd={`url(#${strong ? "cg-arrow-strong" : "cg-arrow"})`}
              opacity={0.75}
            />
            <rect x={x} y={y} width={NODE_W} height={NODE_H} fill="var(--bg-2)" stroke="var(--line)" strokeWidth={1} />
            <text
              x={x + NODE_W / 2}
              y={y + NODE_H / 2 + 4}
              textAnchor="middle"
              style={{ fontSize: 10, fill: "var(--fg-1)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {shortLabel(e.effect)}
            </text>
            <text
              x={x - 5}
              y={y2 - 5}
              textAnchor="end"
              style={{ fontSize: 9, fill: strengthColor(e.evidence_strength) }}
            >
              lag {e.lag}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

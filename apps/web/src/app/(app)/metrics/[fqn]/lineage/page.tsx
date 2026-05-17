"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { GitBranch } from "lucide-react";

interface LNode { id: string; kind: string; label: string }
interface LEdge { source: string; target: string; kind: string; confidence: number }
interface GraphData { nodes: LNode[]; edges: LEdge[]; root: string; direction: string; depth: number }

const NODE_W = 160;
const NODE_H = 36;
const LAYER_GAP = 120;
const NODE_GAP = 60;
const PAD = 40;

function layoutDAG(nodes: LNode[], edges: LEdge[]): Map<string, { x: number; y: number }> {
  const adj: Map<string, string[]> = new Map();
  const indeg: Map<string, number> = new Map();
  nodes.forEach(n => { adj.set(n.id, []); indeg.set(n.id, 0); });
  edges.forEach(e => {
    adj.get(e.source)?.push(e.target);
    indeg.set(e.target, (indeg.get(e.target) ?? 0) + 1);
  });
  const queue = nodes.filter(n => (indeg.get(n.id) ?? 0) === 0).map(n => n.id);
  const layer: Map<string, number> = new Map();
  nodes.forEach(n => layer.set(n.id, 0));
  while (queue.length > 0) {
    const nid = queue.shift()!;
    for (const child of (adj.get(nid) ?? [])) {
      const l = Math.max(layer.get(child) ?? 0, (layer.get(nid) ?? 0) + 1);
      layer.set(child, l);
      const d = (indeg.get(child) ?? 1) - 1;
      indeg.set(child, d);
      if (d === 0) queue.push(child);
    }
  }
  const byLayer: Map<number, string[]> = new Map();
  nodes.forEach(n => {
    const l = layer.get(n.id) ?? 0;
    if (!byLayer.has(l)) byLayer.set(l, []);
    byLayer.get(l)!.push(n.id);
  });
  const positions: Map<string, { x: number; y: number }> = new Map();
  byLayer.forEach((nids, l) => {
    const totalH = nids.length * NODE_H + (nids.length - 1) * NODE_GAP;
    nids.forEach((nid, i) => {
      positions.set(nid, {
        x: l * (NODE_W + LAYER_GAP),
        y: i * (NODE_H + NODE_GAP) - totalH / 2,
      });
    });
  });
  return positions;
}

export default function MetricLineagePage({ params }: { params: Promise<{ fqn: string }> }) {
  const [fqn, setFqn] = useState("");
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<LEdge | null>(null);
  const [depth, setDepth] = useState(3);

  useEffect(() => {
    params.then(p => setFqn(decodeURIComponent(p.fqn)));
  }, [params]);

  useEffect(() => {
    if (!fqn) return;
    setLoading(true);
    setError(null);
    fetch(`/api/v1/lineage/graph?root=${encodeURIComponent(fqn)}&depth=${depth}&direction=both&include_causal=true`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => { setGraph(data); setLoading(false); })
      .catch(() => { setError("Failed to load lineage graph"); setLoading(false); });
  }, [fqn, depth]);

  const positions = graph ? layoutDAG(graph.nodes, graph.edges) : new Map();
  const allX = Array.from(positions.values()).map(p => p.x);
  const allY = Array.from(positions.values()).map(p => p.y);
  const minX = allX.length ? Math.min(...allX) : 0;
  const minY = allY.length ? Math.min(...allY) : 0;
  const maxX = allX.length ? Math.max(...allX) : 0;
  const maxY = allY.length ? Math.max(...allY) : 0;
  const svgW = maxX - minX + NODE_W + PAD * 2;
  const svgH = maxY - minY + NODE_H + PAD * 2;

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-line flex-shrink-0">
          <GitBranch size={16} strokeWidth={1.6} style={{ color: "var(--fg-2)" }} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Link href={`/metrics/${encodeURIComponent(fqn)}`} className="t-small hover:underline" style={{ color: "var(--accent)" }}>
                {fqn}
              </Link>
              <span className="t-micro" style={{ color: "var(--fg-3)" }}>/</span>
              <span className="t-small" style={{ color: "var(--fg-1)" }}>Lineage</span>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>Depth</span>
            {[1, 2, 3, 4, 5].map(d => (
              <button
                key={d}
                onClick={() => setDepth(d)}
                className="w-6 h-6 t-micro flex items-center justify-center border transition-colors"
                style={{
                  background: depth === d ? "var(--accent-bg)" : "var(--bg-2)",
                  color: depth === d ? "var(--accent)" : "var(--fg-2)",
                  borderColor: depth === d ? "var(--accent)" : "var(--line)",
                }}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-auto" style={{ background: "var(--bg-0)" }}>
          {loading && (
            <div className="flex items-center justify-center h-full">
              <span className="t-small" style={{ color: "var(--fg-3)" }}>Loading lineage...</span>
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center h-full">
              <span className="t-small" style={{ color: "var(--fail)" }}>{error}</span>
            </div>
          )}
          {!loading && !error && graph && graph.nodes.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <span className="t-small" style={{ color: "var(--fg-3)" }}>No lineage data for this metric.</span>
            </div>
          )}
          {!loading && !error && graph && graph.nodes.length > 0 && (
            <svg
              width={svgW}
              height={Math.max(svgH, 400)}
              style={{ display: "block", margin: "0 auto" }}
            >
              {graph.edges.map((e, i) => {
                const src = positions.get(e.source);
                const tgt = positions.get(e.target);
                if (!src || !tgt) return null;
                const x1 = src.x - minX + PAD + NODE_W;
                const y1 = src.y - minY + PAD + NODE_H / 2;
                const x2 = tgt.x - minX + PAD;
                const y2 = tgt.y - minY + PAD + NODE_H / 2;
                const mx = (x1 + x2) / 2;
                const isCausal = e.kind === "causality";
                const isSelected = selectedEdge?.source === e.source && selectedEdge?.target === e.target;
                return (
                  <g key={i} onClick={() => setSelectedEdge(isSelected ? null : e)} style={{ cursor: "pointer" }}>
                    <path
                      d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
                      fill="none"
                      stroke={isSelected ? "var(--accent)" : isCausal ? "var(--accent)" : "var(--line)"}
                      strokeWidth={isSelected ? 2 : isCausal ? 1.5 : 1}
                      strokeDasharray={isCausal ? "4 3" : undefined}
                      opacity={isCausal ? Math.max(0.4, e.confidence) : 0.6}
                    />
                    <circle cx={x2} cy={y2} r={3} fill={isCausal ? "var(--accent)" : "var(--fg-3)"} />
                  </g>
                );
              })}
              {graph.nodes.map(n => {
                const pos = positions.get(n.id);
                if (!pos) return null;
                const nx = pos.x - minX + PAD;
                const ny = pos.y - minY + PAD;
                const isRoot = n.id === graph.root;
                return (
                  <g key={n.id}>
                    <rect
                      x={nx} y={ny} width={NODE_W} height={NODE_H}
                      fill={isRoot ? "var(--accent-bg)" : "var(--bg-1)"}
                      stroke={isRoot ? "var(--accent)" : "var(--line)"}
                      strokeWidth={isRoot ? 1.5 : 1}
                    />
                    <text
                      x={nx + 8} y={ny + NODE_H / 2 + 4}
                      fontSize={11}
                      fill={isRoot ? "var(--accent)" : "var(--fg-0)"}
                      fontFamily="var(--font-jetbrains-mono)"
                    >
                      {n.label.length > 18 ? n.label.slice(0, 17) + "…" : n.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      </div>

      {selectedEdge && (
        <div className="border-l border-line p-5 flex-shrink-0" style={{ width: 320, background: "var(--bg-1)" }}>
          <div className="flex items-center justify-between mb-4">
            <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Edge detail</span>
            <button onClick={() => setSelectedEdge(null)} className="t-small hover:opacity-70" style={{ color: "var(--fg-3)" }}>x</button>
          </div>
          <div className="space-y-3">
            <div>
              <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Source</span>
              <span className="t-small font-mono" style={{ color: "var(--accent)" }}>{selectedEdge.source}</span>
            </div>
            <div>
              <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Target</span>
              <span className="t-small font-mono" style={{ color: "var(--accent)" }}>{selectedEdge.target}</span>
            </div>
            <div>
              <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Kind</span>
              <span className="t-small font-mono" style={{ color: "var(--fg-1)" }}>{selectedEdge.kind}</span>
            </div>
            <div>
              <span className="t-micro block mb-0.5" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Confidence</span>
              <span className="t-small font-mono" style={{ color: "var(--fg-1)" }}>{(selectedEdge.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

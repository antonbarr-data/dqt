"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { GitBranch, Plus, Upload, Trash2, X } from "lucide-react";

interface LNode { id: string; kind: string; label: string }
interface LEdge { id: string; source: string; target: string; kind: string; confidence: number }
interface GraphData { nodes: LNode[]; edges: LEdge[]; root: string | null; direction: string; depth: number }

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

interface AddEdgeForm {
  upstream_node: string;
  upstream_label: string;
  downstream_node: string;
  downstream_label: string;
  kind: string;
  confidence: string;
}

const EMPTY_FORM: AddEdgeForm = {
  upstream_node: "",
  upstream_label: "",
  downstream_node: "",
  downstream_label: "",
  kind: "column_lineage",
  confidence: "1.0",
};

export default function LineagePage() {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<LEdge | null>(null);
  const [depth, setDepth] = useState(3);
  const [showAddEdge, setShowAddEdge] = useState(false);
  const [addForm, setAddForm] = useState<AddEdgeForm>(EMPTY_FORM);
  const [addSaving, setAddSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadGraph = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch(`/api/v1/lineage/graph?depth=${depth}&direction=both&include_causal=true`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => { setGraph(data); setLoading(false); })
      .catch(() => { setError("Failed to load lineage graph"); setLoading(false); });
  }, [depth]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  async function handleAddEdge() {
    setAddSaving(true);
    try {
      const res = await fetch("/api/v1/lineage/edges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          upstream_node: addForm.upstream_node,
          upstream_label: addForm.upstream_label || addForm.upstream_node,
          downstream_node: addForm.downstream_node,
          downstream_label: addForm.downstream_label || addForm.downstream_node,
          kind: addForm.kind,
          confidence: parseFloat(addForm.confidence) || 1.0,
        }),
      });
      if (res.ok) {
        setShowAddEdge(false);
        setAddForm(EMPTY_FORM);
        loadGraph();
      }
    } finally {
      setAddSaving(false);
    }
  }

  async function handleDeleteEdge(edgeId: string) {
    setDeleting(true);
    try {
      const res = await fetch(`/api/v1/lineage/edges/${edgeId}`, { method: "DELETE" });
      if (res.ok) {
        setSelectedEdge(null);
        loadGraph();
      }
    } finally {
      setDeleting(false);
    }
  }

  async function handleDbtImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/v1/lineage/import-dbt", { method: "POST", body: form });
      if (res.ok) {
        const data = await res.json();
        setImportResult(`Imported ${data.imported} edges from dbt manifest`);
        loadGraph();
      } else {
        setImportResult("Import failed");
      }
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

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
        {/* header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-line flex-shrink-0">
          <GitBranch size={16} strokeWidth={1.6} style={{ color: "var(--fg-2)" }} />
          <span className="t-h2 flex-1" style={{ color: "var(--fg-0)" }}>Lineage</span>
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
            <button
              onClick={() => setShowAddEdge(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2 ml-2"
              style={{ color: "var(--fg-1)" }}
            >
              <Plus size={11} strokeWidth={1.6} />
              Add edge
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={importing}
              className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2 disabled:opacity-50"
              style={{ color: "var(--fg-1)" }}
            >
              <Upload size={11} strokeWidth={1.6} />
              {importing ? "Importing..." : "Upload dbt manifest"}
            </button>
            <input ref={fileInputRef} type="file" accept=".json" className="hidden" onChange={handleDbtImport} />
          </div>
        </div>

        {/* legend */}
        <div className="flex items-center gap-4 px-6 py-2 border-b border-line flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <svg width={20} height={10}>
              <line x1={0} y1={5} x2={20} y2={5} stroke="var(--line)" strokeWidth={1} />
              <circle cx={17} cy={5} r={3} fill="var(--fg-3)" />
            </svg>
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>Column lineage</span>
          </div>
          <div className="flex items-center gap-1.5">
            <svg width={20} height={10}>
              <line x1={0} y1={5} x2={20} y2={5} stroke="var(--accent)" strokeWidth={1.5} strokeDasharray="4 3" />
              <circle cx={17} cy={5} r={3} fill="var(--accent)" />
            </svg>
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>Causal / dbt edge</span>
          </div>
          {importResult && (
            <span className="t-micro ml-auto" style={{ color: "var(--pass)" }}>{importResult}</span>
          )}
        </div>

        {/* canvas */}
        <div className="flex-1 overflow-auto" style={{ background: "var(--bg-0)" }}>
          {loading && (
            <div className="flex items-center justify-center h-full">
              <span className="t-small" style={{ color: "var(--fg-3)" }}>Loading lineage graph...</span>
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center h-full">
              <span className="t-small" style={{ color: "var(--fail)" }}>{error}</span>
            </div>
          )}
          {!loading && !error && graph && graph.nodes.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <GitBranch size={32} strokeWidth={1} style={{ color: "var(--fg-3)" }} />
              <p className="t-small" style={{ color: "var(--fg-3)" }}>No lineage edges yet.</p>
              <p className="t-micro text-center" style={{ color: "var(--fg-3)", maxWidth: 320 }}>
                Add edges manually, or upload a dbt <code>manifest.json</code> to import your model dependency graph.
              </p>
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={() => setShowAddEdge(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2"
                  style={{ color: "var(--fg-1)" }}
                >
                  <Plus size={11} strokeWidth={1.6} />
                  Add edge
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2"
                  style={{ color: "var(--fg-1)" }}
                >
                  <Upload size={11} strokeWidth={1.6} />
                  Upload dbt manifest
                </button>
              </div>
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
                const isCausal = e.kind !== "column_lineage";
                const isSelected = selectedEdge?.id === e.id;
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
                return (
                  <g key={n.id}>
                    <rect x={nx} y={ny} width={NODE_W} height={NODE_H} fill="var(--bg-1)" stroke="var(--line)" strokeWidth={1} />
                    <text x={nx + 8} y={ny + NODE_H / 2 + 4} fontSize={11} fill="var(--fg-0)" fontFamily="var(--font-jetbrains-mono)">
                      {n.label.length > 18 ? n.label.slice(0, 17) + "…" : n.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      </div>

      {/* edge detail panel */}
      {selectedEdge && (
        <div className="border-l border-line p-5 flex-shrink-0" style={{ width: 320, background: "var(--bg-1)" }}>
          <div className="flex items-center justify-between mb-4">
            <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Edge detail</span>
            <button onClick={() => setSelectedEdge(null)} className="t-small hover:opacity-70" style={{ color: "var(--fg-3)" }}>
              <X size={14} />
            </button>
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
          <button
            onClick={() => handleDeleteEdge(selectedEdge.id)}
            disabled={deleting}
            className="flex items-center gap-1.5 mt-6 px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-50"
            style={{ borderColor: "var(--fail)", color: "var(--fail)" }}
          >
            <Trash2 size={11} strokeWidth={1.6} />
            {deleting ? "Deleting..." : "Delete edge"}
          </button>
        </div>
      )}

      {/* add edge dialog */}
      {showAddEdge && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: "rgba(0,0,0,0.5)" }}>
          <div className="border border-line p-6" style={{ background: "var(--bg-1)", width: 420 }}>
            <div className="flex items-center justify-between mb-4">
              <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Add lineage edge</span>
              <button onClick={() => { setShowAddEdge(false); setAddForm(EMPTY_FORM); }} style={{ color: "var(--fg-3)" }}>
                <X size={14} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="t-micro block mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Upstream node ID</label>
                <input
                  className="w-full px-2 py-1.5 t-small border border-line bg-transparent outline-none focus:border-accent font-mono"
                  style={{ color: "var(--fg-0)" }}
                  placeholder="dataset.column"
                  value={addForm.upstream_node}
                  onChange={e => setAddForm(f => ({ ...f, upstream_node: e.target.value }))}
                />
              </div>
              <div>
                <label className="t-micro block mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Upstream label (optional)</label>
                <input
                  className="w-full px-2 py-1.5 t-small border border-line bg-transparent outline-none focus:border-accent"
                  style={{ color: "var(--fg-0)" }}
                  placeholder="Human-readable name"
                  value={addForm.upstream_label}
                  onChange={e => setAddForm(f => ({ ...f, upstream_label: e.target.value }))}
                />
              </div>
              <div>
                <label className="t-micro block mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Downstream node ID</label>
                <input
                  className="w-full px-2 py-1.5 t-small border border-line bg-transparent outline-none focus:border-accent font-mono"
                  style={{ color: "var(--fg-0)" }}
                  placeholder="dataset.column"
                  value={addForm.downstream_node}
                  onChange={e => setAddForm(f => ({ ...f, downstream_node: e.target.value }))}
                />
              </div>
              <div>
                <label className="t-micro block mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Downstream label (optional)</label>
                <input
                  className="w-full px-2 py-1.5 t-small border border-line bg-transparent outline-none focus:border-accent"
                  style={{ color: "var(--fg-0)" }}
                  placeholder="Human-readable name"
                  value={addForm.downstream_label}
                  onChange={e => setAddForm(f => ({ ...f, downstream_label: e.target.value }))}
                />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="t-micro block mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Kind</label>
                  <select
                    className="w-full px-2 py-1.5 t-small border border-line bg-transparent outline-none focus:border-accent"
                    style={{ color: "var(--fg-0)", background: "var(--bg-1)" }}
                    value={addForm.kind}
                    onChange={e => setAddForm(f => ({ ...f, kind: e.target.value }))}
                  >
                    <option value="column_lineage">column_lineage</option>
                    <option value="causality">causality</option>
                    <option value="manual">manual</option>
                  </select>
                </div>
                <div style={{ width: 80 }}>
                  <label className="t-micro block mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Confidence</label>
                  <input
                    className="w-full px-2 py-1.5 t-small border border-line bg-transparent outline-none focus:border-accent font-mono"
                    style={{ color: "var(--fg-0)" }}
                    placeholder="0.0-1.0"
                    value={addForm.confidence}
                    onChange={e => setAddForm(f => ({ ...f, confidence: e.target.value }))}
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => { setShowAddEdge(false); setAddForm(EMPTY_FORM); }}
                className="px-3 py-1.5 t-small border border-line hover:bg-bg-2 transition-colors"
                style={{ color: "var(--fg-2)" }}
              >
                Cancel
              </button>
              <button
                onClick={handleAddEdge}
                disabled={!addForm.upstream_node || !addForm.downstream_node || addSaving}
                className="px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
                style={{ background: "var(--accent-bg)", borderColor: "var(--accent)", color: "var(--accent)" }}
              >
                {addSaving ? "Saving..." : "Add edge"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

"use client"

import { useState, useRef, useCallback } from "react"

const NODE_DEFS: Record<string, { short: string; dataset: string; kind: "null_rate" | "row_count" }> = {
  null_rate_prices: { short: "price_nulls",  dataset: "gig_prices",          kind: "null_rate" },
  null_rate_vendor: { short: "vendor_nulls", dataset: "gig_vendor_stats",     kind: "null_rate" },
  row_count_vendor: { short: "vendor_rows",  dataset: "gig_vendor_stats",     kind: "row_count" },
  null_rate_txn:    { short: "txn_nulls",    dataset: "gigler_transactions",  kind: "null_rate" },
  row_count_txn:    { short: "txn_rows",     dataset: "gigler_transactions",  kind: "row_count" },
  null_rate_mktg:   { short: "mktg_nulls",   dataset: "marketing_campaigns",  kind: "null_rate" },
}

const EDGE_DEFS = [
  { from: "null_rate_prices", to: "null_rate_txn",  weight: 0.72, lag: "0d", method: "Granger",          evidence: "price_id is FK in transactions" },
  { from: "null_rate_vendor", to: "null_rate_mktg", weight: 0.61, lag: "1d", method: "Transfer Entropy", evidence: "vendor_id is FK in campaigns" },
  { from: "null_rate_txn",    to: "null_rate_mktg", weight: 0.44, lag: "0d", method: "Granger",          evidence: "platform drives campaign targeting" },
  { from: "row_count_vendor", to: "row_count_txn",  weight: 0.38, lag: "1d", method: "CCM",              evidence: "vendor count correlates with transaction volume" },
  { from: "row_count_txn",    to: "null_rate_mktg", weight: 0.29, lag: "2d", method: "Granger",          evidence: "high txn volume - data pipeline pressure - nulls" },
] as const

const POSITIONS: Record<string, { x: number; y: number }> = {
  null_rate_prices: { x: 30,  y: 30  },
  null_rate_vendor: { x: 30,  y: 140 },
  row_count_vendor: { x: 30,  y: 250 },
  null_rate_txn:    { x: 260, y: 80  },
  row_count_txn:    { x: 260, y: 200 },
  null_rate_mktg:   { x: 490, y: 130 },
}

const W = 110
const H = 40

const METHOD_DESC: Record<string, string> = {
  "Granger":          "Does A's past predict B beyond B's own history? (linear, parametric)",
  "Transfer Entropy": "How much does A reduce uncertainty about B's future? (non-linear, model-free)",
  "CCM":              "Do A and B share attractor geometry? (coupled dynamics, no clean lead-lag needed)",
}

function strengthLabel(w: number) {
  return w >= 0.6 ? "strong" : w >= 0.4 ? "moderate" : "weak"
}

function formatValue(id: string, v: number): string {
  if (id.startsWith("null_rate_")) return `${(v * 100).toFixed(2)}%`
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(v)
}

function nodeColor(id: string, v: number): string {
  if (id.startsWith("null_rate_")) {
    const pct = v * 100
    if (pct >= 10) return "var(--fail)"
    if (pct >= 2) return "var(--warn)"
    return "var(--pass)"
  }
  return "var(--accent)"
}

function edgeColor(w: number): string {
  if (w >= 0.6) return "var(--fail)"
  if (w >= 0.4) return "var(--warn)"
  return "var(--pass)"
}

interface TooltipState {
  x: number
  y: number
  title: string
  rows: { label: string; value: string }[]
}

export function CausalDAG({ metricValues }: { metricValues: Record<string, number> }) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const showNode = useCallback((e: React.MouseEvent, id: string) => {
    const def = NODE_DEFS[id]
    if (!def) return
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    const v = metricValues[id] ?? 0
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      title: def.short,
      rows: [
        { label: "Dataset", value: def.dataset },
        { label: "Metric",  value: def.kind === "null_rate" ? "Null rate — fraction of rows containing at least one null" : "Row count — total rows ingested in the last pipeline run" },
        { label: "Value",   value: formatValue(id, v) },
      ],
    })
  }, [metricValues])

  const showEdge = useCallback((e: React.MouseEvent, edge: (typeof EDGE_DEFS)[number]) => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      title: `${NODE_DEFS[edge.from]?.short} → ${NODE_DEFS[edge.to]?.short}`,
      rows: [
        { label: "Strength", value: `${edge.weight.toFixed(2)} — ${strengthLabel(edge.weight)} (0-1 causal coefficient, not a percentage)` },
        { label: "Method",   value: `${edge.method}: ${METHOD_DESC[edge.method]}` },
        { label: "Lag",      value: edge.lag === "0d" ? "same-day effect (0d)" : `${edge.lag} — upstream change takes this long to propagate` },
        { label: "Evidence", value: edge.evidence },
      ],
    })
  }, [])

  const hide = useCallback(() => setTooltip(null), [])

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%", height: "100%" }}>
      <svg width="100%" viewBox="0 0 660 320" style={{ overflow: "visible" }}>
        <defs>
          <marker id="arrow-causal" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="var(--fg-3)" />
          </marker>
        </defs>

        {EDGE_DEFS.map((e, i) => {
          const from = POSITIONS[e.from]
          const to = POSITIONS[e.to]
          if (!from || !to) return null
          const x1 = from.x + W, y1 = from.y + H / 2
          const x2 = to.x - 6,   y2 = to.y + H / 2
          const mx = (x1 + x2) / 2
          const color = edgeColor(e.weight)
          return (
            <g key={i} onMouseEnter={(ev) => showEdge(ev, e)} onMouseLeave={hide} style={{ cursor: "crosshair" }}>
              {/* wide invisible hit area */}
              <path d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`} stroke="transparent" strokeWidth={14} fill="none" />
              <path
                d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
                stroke={color} strokeWidth={1 + e.weight * 2} fill="none"
                strokeOpacity={0.75} markerEnd="url(#arrow-causal)"
              />
              <text x={mx} y={(y1 + y2) / 2 - 4} fontSize="11" fill="var(--fg-2)" fontFamily="var(--font-jetbrains-mono)" textAnchor="middle">
                {e.weight.toFixed(2)}
              </text>
            </g>
          )
        })}

        {Object.entries(POSITIONS).map(([id, pos]) => {
          const def = NODE_DEFS[id]
          if (!def) return null
          const v = metricValues[id] ?? 0
          const color = nodeColor(id, v)
          const isSelected = id === "null_rate_mktg"
          return (
            <g key={id} onMouseEnter={(ev) => showNode(ev, id)} onMouseLeave={hide} style={{ cursor: "pointer" }}>
              <rect
                x={pos.x} y={pos.y} width={W} height={H}
                fill="var(--bg-2)"
                stroke={isSelected ? "var(--accent)" : "var(--line)"}
                strokeWidth={isSelected ? 1.5 : 1}
              />
              <circle cx={pos.x + 10} cy={pos.y + 13} r={4} fill={color} />
              <text x={pos.x + 20} y={pos.y + 16} fontSize="10" fill="var(--fg-0)" fontFamily="var(--font-jetbrains-mono)">{def.short}</text>
              <text x={pos.x + 10} y={pos.y + 30} fontSize="9" fill={color} fontFamily="var(--font-jetbrains-mono)" fontWeight="500">{formatValue(id, v)}</text>
            </g>
          )
        })}
      </svg>

      {tooltip && (
        <div style={{
          position: "absolute",
          left: tooltip.x + 16,
          top: tooltip.y - 8,
          background: "var(--bg-1)",
          border: "1px solid var(--line-3)",
          padding: "8px 10px",
          pointerEvents: "none",
          zIndex: 20,
          minWidth: 260,
          maxWidth: 360,
        }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", marginBottom: 6 }}>
            {tooltip.title}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {tooltip.rows.map((r, i) => (
              <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                <span style={{ fontSize: 10, color: "var(--fg-3)", minWidth: 58, flexShrink: 0, textTransform: "uppercase", letterSpacing: "0.06em", paddingTop: 1 }}>
                  {r.label}
                </span>
                <span style={{ fontSize: 11, color: "var(--fg-1)", lineHeight: 1.5 }}>
                  {r.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

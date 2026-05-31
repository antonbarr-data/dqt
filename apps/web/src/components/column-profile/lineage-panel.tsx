"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface LineageNode {
  id: string;
  kind: string;
  label: string;
}

interface LineageEdge {
  id: string;
  source: string;
  target: string;
  kind: string;
  confidence: number;
}

interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
  root: string | null;
}

function NodePill({ node, isRoot }: { node: LineageNode; isRoot: boolean }) {
  const parts = node.id.split(".");
  const label = node.label || parts[parts.length - 1];
  const schema = parts.length > 1 ? parts.slice(0, -1).join(".") : null;

  return (
    <div
      className="px-3 py-2 border border-line"
      style={{
        background: isRoot ? "var(--bg-2)" : "var(--bg-0)",
        borderColor: isRoot ? "var(--accent)" : "var(--line)",
      }}
    >
      <p className="t-small font-mono truncate" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>{label}</p>
      {schema && <p className="t-micro truncate" style={{ color: "var(--fg-3)" }}>{schema}</p>}
    </div>
  );
}

export function LineagePanel({
  datasetId,
  column,
}: {
  datasetId: string;
  column: string;
}) {
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [loading, setLoading] = useState(true);

  const nodeId = `${datasetId}.${column}`;

  useEffect(() => {
    fetch(`/api/v1/lineage/graph?root=${encodeURIComponent(nodeId)}&direction=both&depth=2`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { setGraph(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [nodeId]);

  const upstream = graph
    ? graph.edges
        .filter(e => e.target === nodeId)
        .map(e => graph.nodes.find(n => n.id === e.source))
        .filter((n): n is LineageNode => n !== undefined)
    : [];

  const downstream = graph
    ? graph.edges
        .filter(e => e.source === nodeId)
        .map(e => graph.nodes.find(n => n.id === e.target))
        .filter((n): n is LineageNode => n !== undefined)
    : [];

  const hasLineage = upstream.length > 0 || downstream.length > 0;

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Lineage
        </span>
        {hasLineage && (
          <Link
            href="/lineage"
            className="t-micro hover:opacity-80"
            style={{ color: "var(--accent)" }}
          >
            full graph
          </Link>
        )}
      </div>

      {loading ? (
        <div className="px-4 py-4 t-small" style={{ color: "var(--fg-3)" }}>Loading...</div>
      ) : !hasLineage ? (
        <div className="px-4 py-4">
          <p className="t-small mb-2" style={{ color: "var(--fg-3)" }}>No lineage configured for this column.</p>
          <p className="t-micro" style={{ color: "var(--fg-3)" }}>
            Set up lineage by importing a dbt manifest or adding edges via the{" "}
            <Link href="/lineage" className="hover:opacity-80" style={{ color: "var(--accent)" }}>
              Lineage
            </Link>{" "}
            page.
          </p>
        </div>
      ) : (
        <div className="px-4 py-3 flex flex-col gap-3">
          {upstream.length > 0 && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                Upstream ({upstream.length})
              </p>
              <div className="flex flex-col gap-1.5">
                {upstream.map(n => <NodePill key={n.id} node={n} isRoot={false} />)}
              </div>
            </div>
          )}
          {/* Current node */}
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              This column
            </p>
            <NodePill
              node={{ id: nodeId, kind: "column", label: column }}
              isRoot
            />
          </div>
          {downstream.length > 0 && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                Downstream ({downstream.length})
              </p>
              <div className="flex flex-col gap-1.5">
                {downstream.map(n => <NodePill key={n.id} node={n} isRoot={false} />)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

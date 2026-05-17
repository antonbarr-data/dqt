"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";

interface MetricSummary {
  fqn: string;
  display_name: string;
  kind: string;
  dataset: string;
  owners: string[];
  tags: string[];
  current_verdict: string | null;
  last_run: string | null;
  pinned: boolean;
}

function VerdictDot({ verdict }: { verdict: string | null }) {
  const color =
    verdict === "pass" ? "var(--pass)" :
    verdict === "fail" ? "var(--fail)" :
    verdict === "warn" ? "var(--warn)" : "var(--fg-3)";
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8, flexShrink: 0,
      background: color, boxShadow: `0 0 0 2px ${color}28`,
    }} />
  );
}

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<MetricSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");

  const search = useCallback(async (query: string, status: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ q: query, limit: "50" });
      if (status) params.set("status", status);
      const resp = await fetch(`/api/v1/metrics/search?${params}`);
      if (resp.ok) setResults(await resp.json());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => search(q, statusFilter), 200);
    return () => clearTimeout(timer);
  }, [q, statusFilter, search]);

  useEffect(() => { search("", ""); }, [search]);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Search</h1>
      </div>
      <div className="flex gap-2 mb-4">
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Search metrics by name or fqn..."
          autoFocus
          className="flex-1 border border-line px-3 py-2 t-small bg-transparent outline-none focus:border-accent transition-colors"
          style={{ color: "var(--fg-0)" }}
        />
      </div>
      <div className="flex gap-2 mb-6">
        {["", "pass", "warn", "fail"].map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className="t-micro px-2 py-1 border transition-colors"
            style={{
              borderColor: statusFilter === s ? "var(--accent)" : "var(--line)",
              color: statusFilter === s ? "var(--accent)" : "var(--fg-2)",
              background: statusFilter === s ? "var(--accent-bg)" : "var(--bg-1)",
              letterSpacing: "0.06em",
            }}
          >
            {s === "" ? "All" : s}
          </button>
        ))}
      </div>
      <div className="mb-3">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          {loading ? "Searching..." : `${results.length} result${results.length !== 1 ? "s" : ""}`}
        </span>
      </div>
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr className="border-b border-line">
              {["", "Metric", "Dataset", "Kind", "Owner", "Last run"].map((h, i) => (
                <th key={i} className="px-3 py-2 text-left t-micro"
                    style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.length === 0 && !loading ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center t-small" style={{ color: "var(--fg-3)" }}>
                  {q ? `No metrics match "${q}".` : "No metrics tracked yet."}
                </td>
              </tr>
            ) : results.map(m => (
              <tr key={m.fqn} className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors">
                <td className="px-3 py-2" style={{ width: 32 }}>
                  <VerdictDot verdict={m.current_verdict} />
                </td>
                <td className="px-3 py-2">
                  <Link href={`/metrics/${encodeURIComponent(m.fqn)}`}
                        className="t-small font-mono hover:underline"
                        style={{ color: "var(--accent)" }}>
                    {m.display_name}
                  </Link>
                  <p className="t-micro mt-0.5 font-mono" style={{ color: "var(--fg-3)" }}>{m.fqn}</p>
                </td>
                <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>{m.dataset}</td>
                <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-2)" }}>{m.kind}</td>
                <td className="px-3 py-2 t-small" style={{ color: "var(--fg-2)" }}>{(m.owners || []).join(", ") || "--"}</td>
                <td className="px-3 py-2 t-small" style={{ color: "var(--fg-3)" }}>{m.last_run ?? "--"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

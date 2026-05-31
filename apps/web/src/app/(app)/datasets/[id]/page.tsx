"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";

interface ColumnMeta {
  name: string;
  data_type: string;
  nullable: boolean;
  position: number;
}

interface CheckResult {
  id: number;
  dataset_id: string;
  column: string | null;
  detector: string;
  score: number | null;
  verdict: string | null;
  message: string | null;
  details: Record<string, unknown> | null;
  ran_at_ago: string;
}

interface DatasetDetail {
  id: string;
  source: string;
  schema: string;
  row_count: number | null;
  column_count: number | null;
  check_count: number;
  status: string;
  last_run: string;
  checks: CheckResult[];
}

type Verdict = "pass" | "warn" | "fail" | "unknown";

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const styles: Record<string, { bg: string; color: string }> = {
    pass: { bg: "var(--pass-bg, #0d2a1a)", color: "var(--pass)" },
    warn: { bg: "var(--warn-bg, #2a1f00)", color: "var(--warn)" },
    fail: { bg: "var(--fail-bg)", color: "var(--fail)" },
    unknown: { bg: "var(--bg-2)", color: "var(--fg-3)" },
  };
  const s = styles[verdict] ?? styles.unknown;
  return (
    <span
      className="t-micro px-1.5 py-0.5"
      style={{ background: s.bg, color: s.color, fontFamily: "var(--font-jetbrains-mono)" }}
    >
      {verdict}
    </span>
  );
}

function fmtRows(n: number | null): string {
  if (n === null) return "--";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function TypeBadge({ type }: { type: string }) {
  return (
    <span className="t-micro font-mono px-1.5 py-0.5" style={{ background: "var(--bg-2)", color: "var(--fg-3)" }}>
      {type.toLowerCase()}
    </span>
  );
}

export default function DatasetDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);

  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [columns, setColumns] = useState<ColumnMeta[]>([]);
  const [loadingDataset, setLoadingDataset] = useState(true);
  const [loadingColumns, setLoadingColumns] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    setLoadingDataset(true);
    fetch(`/api/v1/datasets/${encodeURIComponent(id)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { setDataset(d); setLoadingDataset(false); })
      .catch(() => setLoadingDataset(false));
  }, [id]);

  useEffect(() => {
    setLoadingColumns(true);
    fetch(`/api/v1/datasets/${encodeURIComponent(id)}/columns`)
      .then(r => r.ok ? r.json() : [])
      .then((cols: ColumnMeta[]) => { setColumns(cols); setLoadingColumns(false); })
      .catch(() => setLoadingColumns(false));
  }, [id]);

  if (loadingDataset) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={18} className="animate-spin" style={{ color: "var(--fg-3)" }} />
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="p-6">
        <p className="t-small" style={{ color: "var(--fg-3)" }}>Dataset not found.</p>
      </div>
    );
  }

  // Build maps from column name → worst check result + verdict-based DQT score (min across checks) + check count
  const checksByColumn = new Map<string, CheckResult>();
  const dqtScoreByColumn = new Map<string, number>();
  const checkCountByColumn = new Map<string, number>();
  const verdictScore = (v: string | null) => v === "pass" ? 100 : v === "warn" ? 50 : v === "fail" || v === "error" ? 0 : null;
  for (const chk of dataset.checks) {
    if (!chk.column) continue;
    const existing = checksByColumn.get(chk.column);
    const rank = (v: string | null) => v === "fail" ? 3 : v === "warn" ? 2 : v === "pass" ? 1 : 0;
    if (!existing || rank(chk.verdict) > rank(existing.verdict)) {
      checksByColumn.set(chk.column, chk);
    }
    // DQT score = min verdict-based score across all checks for this column
    const vs = verdictScore(chk.verdict);
    if (vs !== null) {
      const prev = dqtScoreByColumn.get(chk.column);
      if (prev === undefined || vs < prev) {
        dqtScoreByColumn.set(chk.column, vs);
      }
    }
    // Count distinct checks per column
    checkCountByColumn.set(chk.column, (checkCountByColumn.get(chk.column) ?? 0) + 1);
  }

  const failCount = dataset.checks.filter(c => c.verdict === "fail").length;
  const warnCount = dataset.checks.filter(c => c.verdict === "warn").length;
  const passCount = dataset.checks.filter(c => c.verdict === "pass").length;

  // Merge columns list with check results
  // Show all columns; if no check data available yet, show loading indicator
  const columnsToShow = columns.length > 0 ? columns : [];

  // Filter by verdict if active
  const filteredColumns = filter
    ? columnsToShow.filter(col => {
        const chk = checksByColumn.get(col.name);
        return (chk?.verdict ?? "unknown") === filter;
      })
    : columnsToShow;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Link href="/datasets" className="flex items-center gap-1.5 t-small transition-colors hover:opacity-80" style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
          <span style={{ fontSize: 14, lineHeight: 1 }}>&#8592;</span>
          <span>Datasets</span>
        </Link>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
        <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{dataset.id}</span>
      </div>
      <div className="flex items-baseline gap-4 mb-6">
        <h1 className="t-h1 font-mono" style={{ color: "var(--fg-0)" }}>{dataset.id}</h1>
        <span className="t-small" style={{ color: "var(--fg-3)" }}>{dataset.source}</span>
      </div>

      {/* KPI band */}
      <div className="grid grid-cols-4 gap-px border border-line mb-8" style={{ background: "var(--line)" }}>
        {[
          { label: "Rows", value: fmtRows(dataset.row_count) },
          { label: "Columns", value: loadingColumns ? "..." : String(columns.length || dataset.column_count || "--") },
          { label: "Checks", value: String(dataset.check_count) },
          { label: "Last run", value: dataset.last_run },
        ].map((k) => (
          <div key={k.label} className="px-5 py-4" style={{ background: "var(--bg-1)" }}>
            <p className="kpi-label mb-1" style={{ color: "var(--fg-2)" }}>{k.label}</p>
            <p className="text-xl font-light font-mono" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>
              {k.value}
            </p>
          </div>
        ))}
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-2 mb-5">
        <button
          onClick={() => setFilter(filter === "pass" ? null : "pass")}
          className="t-small px-2 py-0.5 border transition-colors"
          style={{
            color: "var(--pass)",
            borderColor: filter === "pass" ? "var(--pass)" : "var(--line)",
            background: filter === "pass" ? "rgba(127,179,148,0.1)" : "transparent",
          }}
        >
          {passCount} pass
        </button>
        <button
          onClick={() => setFilter(filter === "warn" ? null : "warn")}
          className="t-small px-2 py-0.5 border transition-colors"
          style={{
            color: "var(--warn)",
            borderColor: filter === "warn" ? "var(--warn)" : "var(--line)",
            background: filter === "warn" ? "rgba(217,181,102,0.1)" : "transparent",
          }}
        >
          {warnCount} warn
        </button>
        <button
          onClick={() => setFilter(filter === "fail" ? null : "fail")}
          className="t-small px-2 py-0.5 border transition-colors"
          style={{
            color: "var(--fail)",
            borderColor: filter === "fail" ? "var(--fail)" : "var(--line)",
            background: filter === "fail" ? "var(--fail-bg)" : "transparent",
          }}
        >
          {failCount} fail
        </button>
        {filter && (
          <button
            onClick={() => setFilter(null)}
            className="t-micro px-1.5 py-0.5 border border-line transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-3)" }}
          >
            clear
          </button>
        )}
      </div>

      {/* Columns table */}
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div
          className="px-3 py-2 border-b border-line t-micro"
          style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
        >
          Columns
          {columns.length > 0 && <span className="ml-2 font-mono">{columns.length}</span>}
        </div>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr className="border-b border-line">
              {["Column", "Type", "Nullable", "Checks", "DQT Score", "Verdict", "Last checked"].map((h) => (
                <th
                  key={h}
                  className="px-3 py-2 text-left t-micro"
                  style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loadingColumns && columns.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center">
                  <Loader2 size={14} className="animate-spin inline" style={{ color: "var(--fg-3)" }} />
                </td>
              </tr>
            ) : filteredColumns.length === 0 && columns.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-4 t-small text-center" style={{ color: "var(--fg-3)" }}>
                  No columns found.
                </td>
              </tr>
            ) : filteredColumns.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-4 t-small text-center" style={{ color: "var(--fg-3)" }}>
                  No {filter} columns.
                </td>
              </tr>
            ) : (
              filteredColumns.map((col) => {
                const chk = checksByColumn.get(col.name);
                const verdict = (chk?.verdict ?? "unknown") as Verdict;
                const scoreInt = dqtScoreByColumn.get(col.name) ?? null;
                const colHref = `/datasets/${encodeURIComponent(id)}/${encodeURIComponent(col.name)}`;
                return (
                  <tr
                    key={col.name}
                    className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors"
                    style={verdict === "fail" ? { background: "var(--fail-bg)" } : undefined}
                  >
                    <td className="px-3 py-2 t-small font-mono">
                      <Link href={colHref as never} className="hover:underline" style={{ color: "var(--accent)" }}>
                        {col.name}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <TypeBadge type={col.data_type} />
                    </td>
                    <td className="px-3 py-2 t-small font-mono" style={{ color: col.nullable ? "var(--fg-3)" : "var(--fg-1)" }}>
                      {col.nullable ? "yes" : "no"}
                    </td>
                    <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-2)" }}>
                      {checkCountByColumn.get(col.name) ?? <span style={{ color: "var(--fg-3)" }}>--</span>}
                    </td>
                    <td className="px-3 py-2">
                      {scoreInt !== null ? (
                        <span
                          className="t-small font-mono"
                          style={{
                            color: scoreInt >= 80 ? "var(--pass)" : scoreInt >= 50 ? "var(--warn)" : "var(--fail)",
                            fontFamily: "var(--font-jetbrains-mono)",
                          }}
                        >
                          {scoreInt}
                        </span>
                      ) : (
                        <span className="t-micro" style={{ color: "var(--fg-3)" }}>--</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {chk ? <VerdictBadge verdict={verdict} /> : (
                        <span className="t-micro" style={{ color: "var(--fg-3)" }}>no check</span>
                      )}
                    </td>
                    <td className="px-3 py-2 t-small" style={{ color: "var(--fg-3)" }}>
                      {chk?.ran_at_ago ?? "--"}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

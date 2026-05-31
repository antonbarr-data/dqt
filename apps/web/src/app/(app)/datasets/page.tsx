"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { Search, BarChart2, ListFilter, X } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ColumnRow {
  source_id: string;
  source_name: string;
  source_engine: string;
  dataset_id: string;
  column: string;
  check_counts: Record<string, number>;
  verdict_counts: Record<string, number>;
  total_checks: number;
  is_metric: boolean;
  worst_verdict: string | null;
  dqt_score: number | null;
}

type FilterKey = "source" | "verdict" | "metric";

interface FilterOption {
  value: string;
  label: string;
  count: number;
  color?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VERDICT_COLOR: Record<string, string> = {
  pass: "var(--pass)", warn: "var(--warn)", fail: "var(--fail)",
  error: "var(--fail)", pending: "var(--fg-3)", unknown: "var(--fg-3)",
};

const ENGINE_ABBR: Record<string, string> = {
  bigquery: "BQ", postgres: "PG", clickhouse: "CH", snowflake: "SF",
  mysql: "MY", databricks: "DB",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// FilterDropdown
// ---------------------------------------------------------------------------

function FilterDropdown({
  options, selected, onChange, onClose, anchorEl,
}: {
  options: FilterOption[];
  selected: Set<string>;
  onChange: (s: Set<string>) => void;
  onClose: () => void;
  anchorEl: HTMLElement | null;
}) {
  const dropRef = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState("");
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  useEffect(() => {
    if (!anchorEl) return;
    const rect = anchorEl.getBoundingClientRect();
    setPos({ top: rect.bottom + 2, left: rect.left });
  }, [anchorEl]);

  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (
        dropRef.current && !dropRef.current.contains(e.target as Node) &&
        anchorEl && !anchorEl.contains(e.target as Node)
      ) onClose();
    }
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") onClose(); }
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose, anchorEl]);

  const visibleOpts = options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()));
  const allChecked = visibleOpts.length > 0 && visibleOpts.every(o => selected.has(o.value));
  const someChecked = visibleOpts.some(o => selected.has(o.value));

  function toggleAll() {
    const next = new Set(selected);
    if (allChecked) visibleOpts.forEach(o => next.delete(o.value));
    else visibleOpts.forEach(o => next.add(o.value));
    onChange(next);
  }

  function toggle(value: string) {
    const next = new Set(selected);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    onChange(next);
  }

  if (!pos) return null;

  const baseInput: React.CSSProperties = {
    background: "var(--bg-2)", color: "var(--fg-0)",
    border: "1px solid var(--line)", outline: "none",
    fontSize: 11, padding: "3px 7px", width: "100%", fontFamily: "inherit",
  };

  return createPortal(
    <div
      ref={dropRef}
      style={{
        position: "fixed", top: pos.top, left: pos.left,
        zIndex: 1000, width: 220,
        background: "var(--bg-1)", border: "1px solid var(--line)",
        boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
      }}
    >
      <div className="p-2 border-b border-line">
        <input autoFocus type="text" placeholder="Search..." value={search}
          onChange={e => setSearch(e.target.value)} style={baseInput} />
      </div>
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-line" style={{ background: "var(--bg-0)" }}>
        <label className="flex items-center gap-2 cursor-pointer t-micro" style={{ color: "var(--fg-1)" }}>
          <input
            type="checkbox" checked={allChecked}
            ref={el => { if (el) el.indeterminate = someChecked && !allChecked; }}
            onChange={toggleAll}
            style={{ accentColor: "var(--accent)", width: 12, height: 12 }}
          />
          Select all ({visibleOpts.length})
        </label>
        {selected.size > 0 && (
          <button
            onClick={() => { onChange(new Set()); onClose(); }}
            className="t-micro hover:underline"
            style={{ color: "var(--accent)", background: "none", border: "none", cursor: "pointer", padding: 0 }}
          >
            Clear
          </button>
        )}
      </div>
      <div style={{ maxHeight: 240, overflowY: "auto" }}>
        {visibleOpts.length === 0 ? (
          <p className="px-3 py-2 t-micro" style={{ color: "var(--fg-3)" }}>No matches</p>
        ) : (
          visibleOpts.map(o => (
            <label
              key={o.value}
              className="flex items-center gap-2 px-2 py-1.5 cursor-pointer"
              style={{ color: "var(--fg-0)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-2)")}
              onMouseLeave={e => (e.currentTarget.style.background = "")}
            >
              <input
                type="checkbox" checked={selected.has(o.value)}
                onChange={() => toggle(o.value)}
                style={{ accentColor: "var(--accent)", width: 12, height: 12, flexShrink: 0 }}
              />
              {o.color && <span style={{ width: 6, height: 6, background: o.color, flexShrink: 0, display: "inline-block" }} />}
              <span className="t-small truncate flex-1">{o.label}</span>
              <span className="t-micro font-mono flex-shrink-0" style={{ color: "var(--fg-3)" }}>{o.count}</span>
            </label>
          ))
        )}
      </div>
    </div>,
    document.body
  );
}

// ---------------------------------------------------------------------------
// FilterHeader
// ---------------------------------------------------------------------------

function FilterHeader({
  label, filterKey, options, selected, openFilter, onOpen, onClose, onChange, headerRef,
}: {
  label: string;
  filterKey: FilterKey;
  options: FilterOption[];
  selected: Set<string>;
  openFilter: FilterKey | null;
  onOpen: (key: FilterKey) => void;
  onClose: () => void;
  onChange: (key: FilterKey, s: Set<string>) => void;
  headerRef: (el: HTMLTableCellElement | null) => void;
}) {
  const cellRef = useRef<HTMLTableCellElement | null>(null);
  const isOpen = openFilter === filterKey;
  const isActive = selected.size > 0;

  return (
    <th
      ref={el => { cellRef.current = el; headerRef(el); }}
      className="px-3 py-2 text-left t-micro select-none"
      style={{ fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase", whiteSpace: "nowrap" }}
    >
      <button
        onClick={() => isOpen ? onClose() : onOpen(filterKey)}
        className="flex items-center gap-1.5"
        style={{
          color: isActive ? "var(--accent)" : isOpen ? "var(--fg-0)" : "var(--fg-2)",
          background: "transparent", border: "none", padding: 0, cursor: "pointer",
          letterSpacing: "0.08em", textTransform: "uppercase",
          fontSize: "inherit", fontFamily: "inherit", fontWeight: "inherit",
        }}
      >
        {label}
        <ListFilter size={10} strokeWidth={1.6} style={{ opacity: isActive || isOpen ? 1 : 0.4 }} />
        {isActive && (
          <span className="font-mono" style={{ fontSize: 9, background: "var(--accent)", color: "var(--bg-0)", padding: "0 3px", lineHeight: "14px", display: "inline-block" }}>
            {selected.size}
          </span>
        )}
      </button>
      {isOpen && (
        <FilterDropdown
          options={options}
          selected={selected}
          onChange={s => onChange(filterKey, s)}
          onClose={onClose}
          anchorEl={cellRef.current}
        />
      )}
    </th>
  );
}

// ---------------------------------------------------------------------------
// CheckSummary
// ---------------------------------------------------------------------------

function CheckSummary({ total, verdictCounts }: { total: number; verdictCounts: Record<string, number> }) {
  if (total === 0) return <span className="t-micro" style={{ color: "var(--fg-3)" }}>--</span>;

  const fail  = (verdictCounts.fail  ?? 0) + (verdictCounts.error ?? 0);
  const warn  = verdictCounts.warn   ?? 0;
  const pass  = verdictCounts.pass   ?? 0;
  const pend  = verdictCounts.pending ?? 0;

  return (
    <div className="flex items-center gap-2.5">
      <span className="t-micro font-mono" style={{ color: "var(--fg-2)" }}>{total}</span>
      <div className="flex items-center gap-2">
        {fail > 0 && <span className="t-micro font-mono" style={{ color: "var(--fail)" }}>{fail} fail</span>}
        {warn > 0 && <span className="t-micro font-mono" style={{ color: "var(--warn)" }}>{warn} warn</span>}
        {pass > 0 && <span className="t-micro font-mono" style={{ color: "var(--pass)" }}>{pass} pass</span>}
        {pend > 0 && fail === 0 && warn === 0 && (
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{pend} pending</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const EMPTY_SET = new Set<string>();

export default function DatasetsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<ColumnRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const [filterSets, setFilterSets] = useState<Record<FilterKey, Set<string>>>({
    source: EMPTY_SET,
    verdict: EMPTY_SET,
    metric: EMPTY_SET,
  });
  const [openFilter, setOpenFilter] = useState<FilterKey | null>(null);
  const headerEls = useRef<Partial<Record<FilterKey, HTMLTableCellElement | null>>>({});

  useEffect(() => {
    fetch("/api/v1/columns")
      .then(r => r.ok ? r.json() : [])
      .then((data: ColumnRow[]) => { setRows(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filterOptions = useMemo((): Record<FilterKey, FilterOption[]> => {
    const count = (arr: string[]) =>
      arr.reduce<Record<string, number>>((acc, v) => { acc[v] = (acc[v] ?? 0) + 1; return acc; }, {});

    const sourceCounts  = count(rows.map(r => r.source_name));
    const verdictCounts = count(rows.map(r => r.worst_verdict ?? "pending"));
    const metricCounts  = count(rows.map(r => r.is_metric ? "yes" : "no"));

    return {
      source: Object.entries(sourceCounts)
        .sort((a, b) => b[1] - a[1])
        .map(([v, n]) => ({ value: v, label: v, count: n })),
      verdict: (["fail", "error", "warn", "pass", "pending"] as const)
        .map(v => ({ value: v, label: v, count: verdictCounts[v] ?? 0, color: VERDICT_COLOR[v] }))
        .filter(o => o.count > 0),
      metric: [
        { value: "yes", label: "Yes", count: metricCounts.yes ?? 0 },
        { value: "no",  label: "No",  count: metricCounts.no  ?? 0 },
      ].filter(o => o.count > 0),
    };
  }, [rows]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter(r => {
      if (filterSets.source.size > 0 && !filterSets.source.has(r.source_name)) return false;
      if (filterSets.verdict.size > 0 && !filterSets.verdict.has(r.worst_verdict ?? "pending")) return false;
      if (filterSets.metric.size > 0 && !filterSets.metric.has(r.is_metric ? "yes" : "no")) return false;
      if (!q) return true;
      return (
        r.source_name.toLowerCase().includes(q) ||
        r.dataset_id.toLowerCase().includes(q) ||
        r.column.toLowerCase().includes(q)
      );
    });
  }, [rows, search, filterSets]);

  function updateFilter(key: FilterKey, s: Set<string>) {
    setFilterSets(prev => ({ ...prev, [key]: s }));
  }

  const filterHeaderProps = (key: FilterKey) => ({
    filterKey: key,
    options: filterOptions[key],
    selected: filterSets[key],
    openFilter,
    onOpen: (k: FilterKey) => setOpenFilter(k),
    onClose: () => setOpenFilter(null),
    onChange: updateFilter,
    headerRef: (el: HTMLTableCellElement | null) => { headerEls.current[key] = el; },
  });

  const hasActiveFilters = Object.values(filterSets).some(s => s.size > 0);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Toolbar */}
      <div
        className="flex items-center gap-3 px-4 py-2.5 border-b border-line"
        style={{ background: "var(--bg-1)", flexShrink: 0 }}
      >
        <div style={{ position: "relative", width: 280 }}>
          <Search size={13} strokeWidth={1.5} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: "var(--fg-3)", pointerEvents: "none" }} />
          <input
            type="text"
            placeholder="Search source, table, column..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              background: "var(--bg-2)", color: "var(--fg-0)", border: "1px solid var(--line)",
              outline: "none", fontSize: 12, padding: "6px 10px 6px 30px",
              fontFamily: "inherit", width: "100%",
            }}
          />
        </div>

        {hasActiveFilters && (
          <button
            onClick={() => setFilterSets({ source: new Set(), verdict: new Set(), metric: new Set() })}
            className="t-micro px-2 py-1 border border-line flex items-center gap-1.5"
            style={{ color: "var(--fg-3)", background: "transparent", cursor: "pointer" }}
          >
            <X size={10} strokeWidth={1.6} />
            Clear filters
          </button>
        )}

        <div className="flex-1" />

        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
          {loading ? "..." : `${filtered.length} columns`}
        </span>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <span className="t-small" style={{ color: "var(--fg-3)" }}>Loading...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <BarChart2 size={24} strokeWidth={1.2} style={{ color: "var(--fg-3)" }} />
            <p className="t-small" style={{ color: "var(--fg-3)" }}>
              {rows.length === 0
                ? "No monitored columns yet. Add checks to columns to see them here."
                : "No columns match the current filter."}
            </p>
          </div>
        ) : (
          <table className="w-full" style={{ borderCollapse: "collapse" }}>
            <thead style={{ position: "sticky", top: 0, zIndex: 2 }}>
              <tr style={{ background: "var(--bg-1)", borderBottom: "1px solid var(--line)" }}>
                <FilterHeader label="Source" {...filterHeaderProps("source")} />
                <th className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  dataset.table.column
                </th>
                <FilterHeader label="Checks" {...filterHeaderProps("verdict")} />
                <th className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase", width: 80 }}>
                  DQT Score
                </th>
                <FilterHeader label="Metric" {...filterHeaderProps("metric")} />
              </tr>
            </thead>
            <tbody>
              {filtered.map(row => (
                <tr
                  key={`${row.dataset_id}.${row.column}`}
                  onClick={() => router.push(`/datasets/${encodeURIComponent(row.dataset_id)}/${encodeURIComponent(row.column)}`)}
                  className="border-b border-line cursor-pointer"
                  style={{ background: "var(--bg-0)" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-2)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "var(--bg-0)")}
                >
                  {/* Source */}
                  <td className="px-3 py-2.5" style={{ width: 200 }}>
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="t-micro font-mono flex-shrink-0"
                        style={{ padding: "1px 4px", background: "var(--bg-3)", color: "var(--fg-2)", border: "1px solid var(--line)", fontSize: 10 }}
                      >
                        {ENGINE_ABBR[row.source_engine.toLowerCase()] ?? row.source_engine.slice(0, 2).toUpperCase()}
                      </span>
                      <span className="t-small truncate" style={{ color: "var(--fg-1)" }} title={row.source_name}>
                        {row.source_name}
                      </span>
                    </div>
                  </td>

                  {/* Path — dataset.table.column dot notation */}
                  <td className="px-3 py-2.5 min-w-0">
                    <span className="font-mono" style={{ fontSize: 12 }} title={`${row.dataset_id}.${row.column}`}>
                      <span style={{ color: "var(--fg-3)" }}>{row.dataset_id}</span>
                      <span style={{ color: "var(--fg-3)" }}>.</span>
                      <span style={{ color: "var(--accent)" }}>{row.column}</span>
                    </span>
                  </td>

                  {/* Checks summary */}
                  <td className="px-3 py-2.5" style={{ width: 300 }}>
                    <CheckSummary total={row.total_checks} verdictCounts={row.verdict_counts} />
                  </td>

                  {/* DQT Score */}
                  <td className="px-3 py-2.5" style={{ width: 80 }}>
                    {row.dqt_score !== null && row.dqt_score !== undefined ? (
                      <span
                        className="t-small font-mono"
                        style={{
                          color: row.dqt_score >= 80 ? "var(--pass)" : row.dqt_score >= 50 ? "var(--warn)" : "var(--fail)",
                          fontFamily: "var(--font-jetbrains-mono)",
                        }}
                      >
                        {row.dqt_score}
                      </span>
                    ) : (
                      <span className="t-micro" style={{ color: "var(--fg-3)" }}>--</span>
                    )}
                  </td>

                  {/* Metric */}
                  <td className="px-3 py-2.5" style={{ width: 80 }}>
                    <span className="t-small font-mono" style={{ color: row.is_metric ? "var(--accent)" : "var(--fg-3)" }}>
                      {row.is_metric ? "Yes" : "No"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

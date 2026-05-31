"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import { X, Play, CalendarClock, Loader2, Trash2, Download, Upload, ListFilter, ChevronDown, Pencil } from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CheckRow {
  id: string;
  group: string;
  dataset: string;
  column: string;
  check: string;
  score: number | null;
  verdict: Verdict;
  params: Record<string, unknown>;
  enabled: boolean;
  plain_english: string | null;
  ran_at: string | null;
}

interface Schedule {
  id: number;
  cadence: "hourly" | "daily" | "weekly" | "monthly";
  run_hour: number;
  run_minute: number;
  days_of_week: number[];
  day_of_month: number;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
}

type Verdict = "pass" | "warn" | "fail" | "pending" | "error";
type Cadence = "hourly" | "daily" | "weekly" | "monthly";
type FilterKey = "dataset_col" | "category" | "check" | "verdict";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORIES = [
  { label: "All",                   group: null,             hint: "Every check across all categories" },
  { label: "Completeness",          group: "completeness",   hint: "Is the data there?" },
  { label: "Validity",              group: "validity",       hint: "Does it match the rules?" },
  { label: "Drift",                 group: "drift",          hint: "Has the distribution shifted?" },
  { label: "Univariate outliers",   group: "outliers_uni",   hint: "Are individual values unusual?" },
  { label: "Multivariate outliers", group: "outliers_multi", hint: "Are rows unusual in combination?" },
  { label: "Time series",           group: "timeseries",     hint: "Did the temporal pattern change?" },
  { label: "Custom",                group: "custom",         hint: "Specialized cases" },
] as const;

const DETECTOR_GROUP: Record<string, string> = {
  // Completeness
  completeness: "completeness", null_fraction: "completeness", volume: "completeness",
  volume_anomaly: "completeness", row_count_in_range: "completeness",
  freshness_seconds_behind: "completeness", schema_change: "completeness",
  // Validity
  uniqueness: "validity", validity: "validity", set_membership: "validity",
  set_exclusion: "validity", regex_match: "validity", value_in_range: "validity",
  string_length_range: "validity", date_format: "validity", string_case: "validity",
  sql_assertion: "validity", date_part_missing: "validity", monotonicity: "validity",
  referential_integrity_rate: "validity", referential_integrity: "validity", column_pair: "validity",
  composite_uniqueness: "validity", max_in_range: "validity", min_in_range: "validity",
  median_in_range: "validity", stddev_in_range: "validity", sum_in_range: "validity",
  cardinality_in_range: "validity", quantile_in_range: "validity",
  numeric_mean_shift: "validity", numeric_mean: "validity",
  // Drift
  ks_pvalue: "drift", ks_drift: "drift", wasserstein_1: "drift", psi: "drift",
  kl_divergence: "drift", js_divergence: "drift", chi_square_drift: "drift",
  cramers_v: "drift", mmd: "drift", mutual_information: "drift", benford_law_fit: "drift",
  // Univariate outliers
  mad_outlier_fraction: "outliers_uni", double_mad_outlier_fraction: "outliers_uni",
  zscore_outlier_fraction: "outliers_uni", adjusted_boxplot_fraction: "outliers_uni",
  iqr_fence: "outliers_uni", grubbs: "outliers_uni", generalized_esd: "outliers_uni",
  outlier_fraction_drift: "outliers_uni",
  // Multivariate outliers
  isolation_forest_fraction: "outliers_multi", mahalanobis_distance: "outliers_multi",
  lof: "outliers_multi", one_class_svm: "outliers_multi", hbos: "outliers_multi",
  ecod: "outliers_multi",
  // Time series
  stl_residual_zscore: "timeseries", cusum: "timeseries", page_hinkley: "timeseries",
  holt_winters: "timeseries", prophet_anomaly: "timeseries", adwin: "timeseries",
  bocpd: "timeseries", matrix_profile: "timeseries",
};

const CATEGORY_LABEL: Record<string, string> = Object.fromEntries(
  CATEGORIES.filter(c => c.group !== null).map(c => [c.group, c.label])
);

const VERDICT_COLOR: Record<string, string> = {
  pass: "var(--pass)", warn: "var(--warn)", fail: "var(--fail)", pending: "var(--fg-3)", error: "var(--fail)",
};

const VERDICT_ORDER = ["error", "fail", "warn", "pending", "pass"];

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function apiToRow(raw: {
  id: string | number; dataset_id: string; column: string | null;
  detector: string; verdict: string | null; score?: number | null;
  params?: Record<string, unknown> | null;
  enabled?: boolean | null;
  plain_english?: string | null;
  ran_at?: string | null;
}): CheckRow {
  return {
    id: String(raw.id),
    group: DETECTOR_GROUP[raw.detector] ?? "custom",
    dataset: raw.dataset_id,
    column: raw.column ?? "(table)",
    check: raw.detector,
    score: raw.score ?? null,
    verdict: ((raw.verdict ?? "pending") as Verdict),
    params: raw.params ?? {},
    enabled: raw.enabled !== false,
    plain_english: raw.plain_english ?? null,
    ran_at: raw.ran_at ?? null,
  };
}

function normalizeFreshnessParams(params: Record<string, unknown>): Record<string, unknown> {
  const warnSecs = params.warn_seconds ?? params.warn_threshold;
  const failSecs = params.fail_seconds ?? params.fail_threshold;
  const out: Record<string, unknown> = {};
  if (warnSecs !== undefined) out.warn_seconds = warnSecs;
  if (failSecs !== undefined) out.fail_seconds = failSecs;
  for (const [k, v] of Object.entries(params)) {
    if (!["warn_threshold", "fail_threshold", "warn_seconds", "fail_seconds"].includes(k)) out[k] = v;
  }
  return out;
}

function checkToYaml(chk: CheckRow): string {
  const lines: string[] = [`check: ${chk.check}`, `table: ${chk.dataset}`];
  if (chk.column !== "(table)") lines.push(`column: ${chk.column}`);
  const params = chk.check === "freshness_seconds_behind"
    ? normalizeFreshnessParams(chk.params)
    : chk.params;
  if (Object.keys(params).length > 0) {
    lines.push("params:");
    for (const [k, v] of Object.entries(params)) lines.push(`  ${k}: ${JSON.stringify(v)}`);
  }
  lines.push(`enabled: ${chk.enabled}`);
  return lines.join("\n");
}

function fmtScore(score: number): string {
  const s = score.toFixed(1);
  return s.endsWith(".0") ? s.slice(0, -2) : s;
}

function computeDqtScore(chk: CheckRow): number | null {
  if (chk.verdict === "pass") return 100;
  if (chk.verdict === "fail") return 0;
  if (chk.verdict !== "warn" || chk.score === null) return null;
  const wt = Number(chk.params?.warn_threshold);
  const ft = Number(chk.params?.fail_threshold);
  if (isNaN(wt) || isNaN(ft)) return 50;
  const range = Math.abs(wt - ft);
  if (range < 1e-9) return 50;
  const t = Math.min(1, Math.max(0, Math.abs(chk.score - ft) / range));
  return Math.round(t * 98 + 1);
}

function downloadYaml(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/yaml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function fmtTime(iso: string | null): string {
  if (!iso) return "--";
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

function fmtNextRun(iso: string | null): string {
  if (!iso) return "--";
  const d = new Date(iso);
  const diff = d.getTime() - Date.now();
  if (diff < 60_000) return "in <1m";
  if (diff < 3_600_000) return `in ${Math.floor(diff / 60_000)}m`;
  if (diff < 86_400_000) return `in ${Math.floor(diff / 3_600_000)}h`;
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function scheduleLabel(s: Schedule): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  const time = `${pad(s.run_hour)}:${pad(s.run_minute)}`;
  if (s.cadence === "hourly") return `Hourly at :${pad(s.run_minute)}`;
  if (s.cadence === "daily") return `Daily at ${time}`;
  if (s.cadence === "weekly") {
    const days = s.days_of_week.length ? s.days_of_week.map(d => DAY_LABELS[d]).join(", ") : "every day";
    return `Weekly on ${days} at ${time}`;
  }
  return `Monthly on day ${s.day_of_month} at ${time}`;
}

// ---------------------------------------------------------------------------
// Filter dropdown (Excel-style)
// ---------------------------------------------------------------------------

interface FilterOption {
  value: string;
  label: string;
  count: number;
  color?: string;
}

function FilterDropdown({
  options,
  selected,
  onChange,
  onClose,
  anchorEl,
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

  const filtered = options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()));
  const allChecked = filtered.length > 0 && filtered.every(o => selected.has(o.value));
  const someChecked = filtered.some(o => selected.has(o.value));

  function toggleAll() {
    const next = new Set(selected);
    if (allChecked) filtered.forEach(o => next.delete(o.value));
    else filtered.forEach(o => next.add(o.value));
    onChange(next);
  }

  function toggle(value: string) {
    const next = new Set(selected);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    onChange(next);
  }

  function clearAll() {
    onChange(new Set());
    onClose();
  }

  if (!pos) return null;

  const baseInput: React.CSSProperties = {
    background: "var(--bg-2)", color: "var(--fg-0)",
    border: "1px solid var(--line)", outline: "none",
    fontSize: 11, padding: "3px 7px", width: "100%",
    fontFamily: "inherit",
  };

  return createPortal(
    <div
      ref={dropRef}
      style={{
        position: "fixed",
        top: pos.top,
        left: pos.left,
        zIndex: 1000,
        width: 240,
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
      }}
    >
      {/* Search */}
      <div className="p-2 border-b border-line">
        <input
          autoFocus
          type="text"
          placeholder="Search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={baseInput}
        />
      </div>

      {/* Select all / Clear */}
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-line" style={{ background: "var(--bg-0)" }}>
        <label className="flex items-center gap-2 cursor-pointer t-micro" style={{ color: "var(--fg-1)" }}>
          <input
            type="checkbox"
            checked={allChecked}
            ref={el => { if (el) el.indeterminate = someChecked && !allChecked; }}
            onChange={toggleAll}
            style={{ accentColor: "var(--accent)", width: 12, height: 12 }}
          />
          Select all ({filtered.length})
        </label>
        {selected.size > 0 && (
          <button onClick={clearAll} className="t-micro hover:underline" style={{ color: "var(--accent)" }}>
            Clear
          </button>
        )}
      </div>

      {/* Options */}
      <div style={{ maxHeight: 240, overflowY: "auto" }}>
        {filtered.length === 0 ? (
          <p className="px-3 py-2 t-micro" style={{ color: "var(--fg-3)" }}>No matches</p>
        ) : (
          filtered.map(o => (
            <label
              key={o.value}
              className="flex items-center gap-2 px-2 py-1.5 cursor-pointer transition-colors"
              style={{ color: "var(--fg-0)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-2)")}
              onMouseLeave={e => (e.currentTarget.style.background = "")}
            >
              <input
                type="checkbox"
                checked={selected.has(o.value)}
                onChange={() => toggle(o.value)}
                style={{ accentColor: "var(--accent)", width: 12, height: 12, flexShrink: 0 }}
              />
              {o.color && (
                <span style={{ width: 6, height: 6, background: o.color, flexShrink: 0, display: "inline-block" }} />
              )}
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
// Filterable column header
// ---------------------------------------------------------------------------

function FilterHeader({
  label,
  filterKey,
  options,
  selected,
  openFilter,
  onOpen,
  onClose,
  onChange,
  headerRef,
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
        className="flex items-center gap-1.5 transition-colors"
        style={{
          color: isActive ? "var(--accent)" : isOpen ? "var(--fg-0)" : "var(--fg-2)",
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          fontSize: "inherit",
          fontFamily: "inherit",
          fontWeight: "inherit",
        }}
      >
        {label}
        <ListFilter
          size={10}
          strokeWidth={1.6}
          style={{ opacity: isActive || isOpen ? 1 : 0.4 }}
        />
        {isActive && (
          <span
            className="font-mono"
            style={{ fontSize: 9, background: "var(--accent)", color: "var(--bg-0)", padding: "0 3px", lineHeight: "14px", display: "inline-block" }}
          >
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
// Sub-components
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Code block with syntax highlighting + copy
// ---------------------------------------------------------------------------

const SQL_KEYWORDS_RE = /\b(SELECT|FROM|WHERE|GROUP|BY|ORDER|HAVING|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|AS|AND|OR|NOT|IN|IS|NULL|LIMIT|WITH|UNION|DISTINCT|COUNT|SUM|AVG|MIN|MAX|CAST|COALESCE|CASE|WHEN|THEN|ELSE|END|OVER|PARTITION|VALUES|INTO|EXCEPT|INTERSECT|BETWEEN|LIKE|EXISTS)\b/gi;

function colorYamlLine(line: string): React.ReactNode {
  if (!line.trim() || line.trim().startsWith("#")) {
    return <span style={{ color: "var(--fg-3)" }}>{line || " "}</span>;
  }
  const leading = line.match(/^(\s*)/)?.[1] ?? "";
  const rest = line.slice(leading.length);
  const ci = rest.indexOf(":");
  if (ci < 0) return <span style={{ color: "var(--fg-1)" }}>{line}</span>;
  const key = rest.slice(0, ci);
  const afterColon = rest.slice(ci + 1);
  const val = afterColon.trim();
  let valColor = "var(--fg-1)";
  if (val === "true" || val === "false") valColor = "var(--warn)";
  else if (val !== "" && !isNaN(Number(val))) valColor = "var(--fg-0)";
  return (
    <>
      {leading && <span>{leading}</span>}
      <span style={{ color: "var(--accent)" }}>{key}</span>
      <span style={{ color: "var(--fg-3)" }}>:</span>
      {afterColon && <span style={{ color: valColor }}>{afterColon}</span>}
    </>
  );
}

function colorSqlLine(line: string): React.ReactNode {
  if (line.trim().startsWith("--")) {
    return <span style={{ color: "var(--fg-3)" }}>{line}</span>;
  }
  const parts: React.ReactNode[] = [];
  let last = 0;
  const re = new RegExp(SQL_KEYWORDS_RE.source, "gi");
  let m: RegExpExecArray | null;
  while ((m = re.exec(line)) !== null) {
    if (m.index > last) parts.push(<span key={`t${last}`} style={{ color: "var(--fg-1)" }}>{line.slice(last, m.index)}</span>);
    parts.push(<span key={`k${m.index}`} style={{ color: "var(--accent)", fontWeight: 500 }}>{m[0].toUpperCase()}</span>);
    last = m.index + m[0].length;
  }
  if (last < line.length) parts.push(<span key={`t${last}`} style={{ color: "var(--fg-1)" }}>{line.slice(last)}</span>);
  return <>{parts}</>;
}

function CodeBlock({ code, language }: { code: string; language: "yaml" | "sql" }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  }
  const colorFn = language === "yaml" ? colorYamlLine : colorSqlLine;
  const lines = code.split("\n");
  return (
    <div style={{ border: "1px solid var(--line)" }}>
      <div className="flex items-center justify-between px-2.5 py-1 border-b border-line" style={{ background: "var(--bg-2)" }}>
        <span className="t-micro" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{language}</span>
        <button
          onClick={copy}
          className="t-micro transition-colors"
          style={{ color: copied ? "var(--pass)" : "var(--fg-3)", background: "none", border: "none", cursor: "pointer", padding: "0 2px" }}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div
        className="t-micro font-mono overflow-x-auto p-2.5"
        style={{ background: "var(--bg-0)", lineHeight: 1.6, whiteSpace: "pre" }}
      >
        {lines.map((line, i) => (
          <div key={i}>{colorFn(line)}</div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Schedule Modal
// ---------------------------------------------------------------------------

function ScheduleModal({ schedules, onClose, onCreated, onDeleted, onToggled }: {
  schedules: Schedule[];
  onClose: () => void;
  onCreated: (s: Schedule) => void;
  onDeleted: (id: number) => void;
  onToggled: (s: Schedule) => void;
}) {
  const [cadence, setCadence] = useState<Cadence>("daily");
  const [runHour, setRunHour] = useState(9);
  const [runMinute, setRunMinute] = useState(0);
  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [dayOfMonth, setDayOfMonth] = useState(1);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const toggleDay = (d: number) =>
    setSelectedDays(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d].sort());

  async function handleAdd() {
    setSaving(true);
    try {
      const res = await fetch("/api/v1/schedules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cadence, run_hour: runHour, run_minute: runMinute, days_of_week: cadence === "weekly" ? selectedDays : [], day_of_month: cadence === "monthly" ? dayOfMonth : 1 }),
      });
      if (res.ok) onCreated(await res.json());
    } finally { setSaving(false); }
  }

  async function handleDelete(id: number) {
    setDeletingId(id);
    try {
      await fetch(`/api/v1/schedules/${id}`, { method: "DELETE" });
      onDeleted(id);
    } finally { setDeletingId(null); }
  }

  async function handleToggle(s: Schedule) {
    const res = await fetch(`/api/v1/schedules/${s.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: !s.enabled }) });
    if (res.ok) onToggled(await res.json());
  }

  const selectStyle: React.CSSProperties = { background: "var(--bg-2)", color: "var(--fg-0)", border: "1px solid var(--line)", padding: "4px 8px" };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.55)" }} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="border border-line" style={{ background: "var(--bg-1)", width: 520, maxHeight: "90vh", overflowY: "auto" }}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="t-h3" style={{ color: "var(--fg-0)" }}>Check Schedule</span>
          <button onClick={onClose} className="flex items-center justify-center w-6 h-6 border border-line hover:bg-bg-2 transition-colors" style={{ color: "var(--fg-2)" }}><X size={12} strokeWidth={1.6} /></button>
        </div>
        <div className="p-4 space-y-5">
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Frequency</p>
            <div className="flex gap-1.5">
              {(["hourly", "daily", "weekly", "monthly"] as Cadence[]).map(c => (
                <button key={c} onClick={() => setCadence(c)} className="px-3 py-1.5 t-small border transition-colors capitalize" style={{ borderColor: cadence === c ? "var(--accent)" : "var(--line)", color: cadence === c ? "var(--accent)" : "var(--fg-1)", background: cadence === c ? "var(--accent-bg)" : "var(--bg-2)" }}>
                  {c.charAt(0).toUpperCase() + c.slice(1)}
                </button>
              ))}
            </div>
          </div>
          {cadence !== "hourly" && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Run at</p>
              <div className="flex items-center gap-2">
                <select value={runHour} onChange={e => setRunHour(Number(e.target.value))} className="t-small font-mono" style={selectStyle}>{HOURS.map(h => <option key={h} value={h}>{String(h).padStart(2, "0")}</option>)}</select>
                <span className="t-small" style={{ color: "var(--fg-2)" }}>:</span>
                <select value={runMinute} onChange={e => setRunMinute(Number(e.target.value))} className="t-small font-mono" style={selectStyle}>{MINUTES.map(m => <option key={m} value={m}>{String(m).padStart(2, "0")}</option>)}</select>
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>UTC</span>
              </div>
            </div>
          )}
          {cadence === "hourly" && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>At minute</p>
              <div className="flex items-center gap-2">
                <span className="t-small font-mono" style={{ color: "var(--fg-3)" }}>:&nbsp;</span>
                <select value={runMinute} onChange={e => setRunMinute(Number(e.target.value))} className="t-small font-mono" style={selectStyle}>{MINUTES.map(m => <option key={m} value={m}>{String(m).padStart(2, "0")}</option>)}</select>
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>past each hour</span>
              </div>
            </div>
          )}
          {cadence === "weekly" && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Repeat on</p>
              <div className="flex gap-1.5">
                {DAY_LABELS.map((label, i) => {
                  const active = selectedDays.includes(i);
                  return <button key={i} onClick={() => toggleDay(i)} className="w-10 py-1.5 t-micro border transition-colors" style={{ borderColor: active ? "var(--accent)" : "var(--line)", color: active ? "var(--accent)" : "var(--fg-2)", background: active ? "var(--accent-bg)" : "var(--bg-2)", fontFamily: "var(--font-jetbrains-mono)" }}>{label.slice(0, 2)}</button>;
                })}
              </div>
            </div>
          )}
          {cadence === "monthly" && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Day of month</p>
              <select value={dayOfMonth} onChange={e => setDayOfMonth(Number(e.target.value))} className="t-small font-mono" style={selectStyle}>{Array.from({ length: 28 }, (_, i) => i + 1).map(d => <option key={d} value={d}>{d}</option>)}</select>
            </div>
          )}
          <button onClick={handleAdd} disabled={saving || (cadence === "weekly" && selectedDays.length === 0)} className={clsx("flex items-center gap-2 px-4 py-1.5 t-small border transition-colors", saving || (cadence === "weekly" && selectedDays.length === 0) ? "opacity-40 cursor-not-allowed" : "hover:opacity-90")} style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}>
            {saving && <Loader2 size={12} strokeWidth={2} className="animate-spin" />}
            Add Schedule
          </button>
          {schedules.length > 0 && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Active Schedules</p>
              <div className="border border-line" style={{ background: "var(--bg-0)" }}>
                {schedules.map((s, i) => (
                  <div key={s.id} className={clsx("flex items-center gap-3 px-3 py-2.5", i > 0 && "border-t border-line")}>
                    <button onClick={() => handleToggle(s)} className="relative border transition-colors shrink-0" style={{ width: 32, height: 18, background: s.enabled ? "var(--accent)" : "var(--bg-2)", borderColor: s.enabled ? "var(--accent)" : "var(--line)" }} title={s.enabled ? "Disable" : "Enable"}>
                      <span style={{ position: "absolute", top: 2, left: s.enabled ? 14 : 2, width: 12, height: 12, background: s.enabled ? "var(--bg-0)" : "var(--fg-3)", transition: "left 0.15s" }} />
                    </button>
                    <div className="flex-1 min-w-0">
                      <p className="t-small" style={{ color: s.enabled ? "var(--fg-0)" : "var(--fg-3)" }}>{scheduleLabel(s)}</p>
                      <p className="t-micro" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
                        {s.last_run_at ? `last: ${fmtTime(s.last_run_at)}` : "never run"}
                        {s.enabled && s.next_run_at ? ` · next: ${fmtNextRun(s.next_run_at)}` : ""}
                      </p>
                    </div>
                    <button onClick={() => handleDelete(s.id)} disabled={deletingId === s.id} className="flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors shrink-0" style={{ color: "var(--fg-3)" }}>
                      {deletingId === s.id ? <Loader2 size={11} strokeWidth={1.6} className="animate-spin" /> : <Trash2 size={11} strokeWidth={1.6} />}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Edit Modal
// ---------------------------------------------------------------------------

type FreshnessUnit = "seconds" | "minutes" | "hours" | "days";
const UNIT_TO_SECONDS: Record<FreshnessUnit, number> = { seconds: 1, minutes: 60, hours: 3600, days: 86400 };

function bestUnit(secs: number): FreshnessUnit {
  if (secs % 86400 === 0) return "days";
  if (secs % 3600 === 0) return "hours";
  if (secs % 60 === 0) return "minutes";
  return "seconds";
}

function readFreshnessSecs(params: Record<string, unknown>, key: "warn" | "fail", fallback: number): number {
  // Accept both warn_seconds/fail_seconds (correct) and warn_threshold/fail_threshold (legacy)
  const v = params[`${key}_seconds`] ?? params[`${key}_threshold`];
  return typeof v === "number" ? v : fallback;
}

function coerceParamValue(raw: string): unknown {
  if (raw === "true") return true;
  if (raw === "false") return false;
  const n = Number(raw);
  return isNaN(n) || raw.trim() === "" ? raw : n;
}

// ---------------------------------------------------------------------------
// Detector param schema
// ---------------------------------------------------------------------------

interface ParamDef {
  name: string;
  label: string;
  type: "text" | "number" | "integer" | "column" | "date";
  required?: boolean;
  default?: string | number | null;
  placeholder?: string;
  hint?: string;
  min?: number;
  max?: number;
  step?: number;
  selectOptions?: { value: string; label: string }[];
}

const DETECTOR_PARAMS: Record<string, ParamDef[]> = {
  // --- completeness / volume / schema ---
  completeness: [],
  null_fraction: [],
  volume: [],
  volume_anomaly: [
    { name: "min_rows", label: "Min rows", type: "integer", default: 1, min: 0 },
    { name: "max_rows", label: "Max rows", type: "integer", default: 1000000000, min: 0 },
  ],
  schema_change: [],
  row_count_in_range: [
    { name: "date_col", label: "Date column", type: "column", required: true, placeholder: "event_date" },
    { name: "start_date", label: "Start date", type: "text", required: true, placeholder: "2024-01-01" },
    { name: "end_date", label: "End date", type: "text", required: true, placeholder: "2024-01-31" },
    { name: "min_rows", label: "Min rows", type: "integer", default: 0, min: 0 },
    { name: "max_rows", label: "Max rows", type: "integer", default: 1000000000, min: 0 },
  ],
  freshness_seconds_behind: [], // handled by dedicated freshness editor

  // --- validity ---
  uniqueness: [],
  validity: [
    { name: "sql_predicate", label: "SQL predicate", type: "text", required: true, placeholder: "amount > 0", hint: "SQL expression that must be true for valid rows." },
  ],
  set_membership: [
    { name: "allowed_values", label: "Allowed values", type: "text", required: true, placeholder: "a, b, c", hint: "Comma-separated. Only these values are permitted." },
  ],
  set_exclusion: [
    { name: "forbidden_values", label: "Forbidden values", type: "text", required: true, placeholder: "DELETED, __test__", hint: "Comma-separated. Rows with these values are violations." },
  ],
  regex_match: [
    { name: "pattern", label: "Regex pattern", type: "text", required: true, placeholder: "^[A-Z0-9]+$", hint: "Python regex — fraction of non-matching rows triggers verdict." },
  ],
  value_in_range: [
    { name: "min_value", label: "Min value (inclusive)", type: "number", placeholder: "-inf" },
    { name: "max_value", label: "Max value (inclusive)", type: "number", placeholder: "inf" },
  ],
  string_length_range: [
    { name: "min_len", label: "Min length", type: "integer", default: 0, min: 0 },
    { name: "max_len", label: "Max length", type: "integer", default: 255, min: 0 },
  ],
  date_format: [
    { name: "date_format", label: "Date format", type: "text", default: "%Y-%m-%d", placeholder: "%Y-%m-%d", hint: "Tokens: %Y %m %d %H %M %S. Non-matching rows are violations." },
  ],
  string_case: [
    { name: "case", label: "Expected case", type: "text", default: "upper", selectOptions: [{ value: "upper", label: "UPPER" }, { value: "lower", label: "lower" }, { value: "title", label: "Title" }] },
  ],
  sql_assertion: [
    { name: "condition", label: "SQL condition", type: "text", required: true, placeholder: "shipped_at IS NULL OR shipped_at >= created_at", hint: "Rows where this is false are violations." },
  ],
  date_part_missing: [
    { name: "granularity", label: "Granularity", type: "text", default: "day", selectOptions: [{ value: "day", label: "Day" }, { value: "hour", label: "Hour" }, { value: "month", label: "Month" }] },
    { name: "lookback_days", label: "Lookback days", type: "integer", default: 30, min: 1 },
  ],
  monotonicity: [
    { name: "direction", label: "Direction", type: "text", default: "increasing", selectOptions: [{ value: "increasing", label: "Increasing" }, { value: "decreasing", label: "Decreasing" }] },
  ],
  referential_integrity_rate: [
    { name: "parent_table", label: "Parent table", type: "text", required: true, placeholder: "schema.table_name" },
    { name: "parent_col", label: "Parent column", type: "text", default: "id", placeholder: "id" },
  ],
  referential_integrity: [
    { name: "parent_table", label: "Parent table", type: "text", required: true, placeholder: "schema.table_name" },
    { name: "parent_col", label: "Parent column", type: "text", default: "id", placeholder: "id" },
  ],
  column_pair: [
    { name: "col_a", label: "Column A", type: "text", required: true, placeholder: "created_at" },
    { name: "col_b", label: "Column B", type: "text", required: true, placeholder: "shipped_at" },
    { name: "operator", label: "Operator", type: "text", default: ">", selectOptions: [
      { value: "==", label: "==" }, { value: "!=", label: "!=" },
      { value: "<", label: "<" }, { value: "<=", label: "<=" },
      { value: ">", label: ">" }, { value: ">=", label: ">=" },
    ]},
  ],
  composite_uniqueness: [
    { name: "key_columns", label: "Key columns", type: "text", required: true, placeholder: "order_id, product_id", hint: "Comma-separated column names forming the composite key." },
  ],

  // --- numeric aggregate bounds ---
  max_in_range: [
    { name: "min_val", label: "Min bound", type: "number", default: 0.0, hint: "Fail if MAX(col) is below this." },
    { name: "max_val", label: "Max bound", type: "number", placeholder: "inf", hint: "Fail if MAX(col) is above this." },
  ],
  min_in_range: [
    { name: "min_val", label: "Min bound", type: "number", default: 0.0, hint: "Fail if MIN(col) is below this." },
    { name: "max_val", label: "Max bound", type: "number", placeholder: "inf", hint: "Fail if MIN(col) is above this." },
  ],
  median_in_range: [
    { name: "min_val", label: "Min bound", type: "number", default: 0.0 },
    { name: "max_val", label: "Max bound", type: "number", placeholder: "inf" },
  ],
  stddev_in_range: [
    { name: "min_val", label: "Min bound", type: "number", default: 0.0 },
    { name: "max_val", label: "Max bound", type: "number", placeholder: "inf" },
  ],
  sum_in_range: [
    { name: "min_val", label: "Min bound", type: "number", default: 0.0 },
    { name: "max_val", label: "Max bound", type: "number", placeholder: "inf" },
  ],
  cardinality_in_range: [
    { name: "min_val", label: "Min cardinality", type: "integer", default: 1, min: 0 },
    { name: "max_val", label: "Max cardinality", type: "integer", placeholder: "unlimited" },
  ],
  quantile_in_range: [
    { name: "quantile", label: "Quantile (0–1)", type: "number", default: 0.95, min: 0, max: 1, step: 0.01 },
    { name: "min_val", label: "Min bound", type: "number", default: 0.0 },
    { name: "max_val", label: "Max bound", type: "number", placeholder: "inf" },
  ],

  // --- drift ---
  ks_pvalue: [],
  ks_drift: [
    { name: "date_col", label: "Date column", type: "column", required: true, placeholder: "e.g. created_at", hint: "Column that holds the row date/timestamp." },
    { name: "reference_days", label: "Reference days (control)", type: "integer", default: 30, min: 1 },
    { name: "current_days", label: "Current days (test)", type: "integer", default: 7, min: 1 },
  ],
  wasserstein_1: [],
  psi: [
    { name: "n_bins", label: "Bins", type: "integer", default: 10, min: 2 },
  ],
  kl_divergence: [
    { name: "n_bins", label: "Bins", type: "integer", default: 10, min: 2 },
  ],
  js_divergence: [
    { name: "n_bins", label: "Bins", type: "integer", default: 10, min: 2 },
  ],
  chi_square_drift: [],
  cramers_v: [],
  mmd: [],
  mutual_information: [
    { name: "n_bins", label: "Bins", type: "integer", default: 20, min: 2 },
  ],
  benford_law_fit: [],

  // --- univariate outliers ---
  mad_outlier_fraction: [
    { name: "threshold", label: "Modified z-score threshold", type: "number", default: 6.5, min: 0, step: 0.5, hint: "3.5 = sensitive, 11 = robust (Iglewicz-Hoaglin)." },
  ],
  double_mad_outlier_fraction: [
    { name: "threshold", label: "Modified z-score threshold", type: "number", default: 6.5, min: 0, step: 0.5, hint: "Asymmetric — separate left/right MAD from the median." },
  ],
  zscore_outlier_fraction: [
    { name: "threshold", label: "Z-score threshold", type: "number", default: 3.0, min: 0, step: 0.1 },
  ],
  adjusted_boxplot_fraction: [
    { name: "h", label: "Fence multiplier (h)", type: "number", default: 2.5, min: 0, step: 0.1, hint: "Medcouple-adjusted Tukey fence. 2.5 is standard." },
  ],
  iqr_fence: [
    { name: "k", label: "IQR multiplier (k)", type: "number", default: 1.5, min: 0, step: 0.1, hint: "1.5 = Tukey standard; 3.0 = extreme outliers only." },
  ],
  grubbs: [],
  generalized_esd: [
    { name: "max_outliers", label: "Max outliers to test", type: "integer", default: 0, min: 0, hint: "0 = auto (5% of n)." },
    { name: "alpha", label: "Alpha", type: "number", default: 0.05, min: 0, max: 1, step: 0.01 },
  ],
  outlier_fraction_drift: [
    { name: "method", label: "Method", type: "text", default: "iqr", selectOptions: [{ value: "iqr", label: "IQR (Tukey)" }, { value: "percentile", label: "Percentile" }, { value: "zscore", label: "Z-score" }] },
    { name: "k", label: "IQR multiplier (k)", type: "number", default: 1.5, min: 0, step: 0.1, hint: "Used when method=iqr." },
  ],

  // --- multivariate outliers (table-level) ---
  isolation_forest_fraction: [
    { name: "reference_pct", label: "Reference percentile", type: "number", default: 5.0, min: 0.1, max: 50, step: 0.5, hint: "Percentile of reference scores used as outlier threshold. Lower = stricter." },
  ],
  mahalanobis_distance: [
    { name: "p_threshold", label: "Chi-square p threshold", type: "number", default: 0.001, min: 0.0001, max: 0.1, step: 0.001, hint: "Rows beyond the chi-square ellipsoid at this p-value are outliers." },
  ],
  lof: [
    { name: "n_neighbors", label: "Neighbours", type: "integer", placeholder: "auto", min: 1, hint: "Leave blank to auto-select." },
  ],
  one_class_svm: [
    { name: "nu", label: "Nu (outlier fraction bound)", type: "number", default: 0.01, min: 0.001, max: 1, step: 0.01, hint: "Upper bound on the fraction of outliers (0–1)." },
    { name: "kernel", label: "Kernel", type: "text", default: "rbf", selectOptions: [{ value: "rbf", label: "RBF" }, { value: "linear", label: "Linear" }, { value: "poly", label: "Poly" }, { value: "sigmoid", label: "Sigmoid" }] },
  ],
  hbos: [
    { name: "n_bins", label: "Histogram bins", type: "integer", default: 20, min: 2 },
  ],
  ecod: [],

  // --- time series ---
  stl_residual_zscore: [
    { name: "period", label: "Season length", type: "integer", min: 2, placeholder: "auto", hint: "Observations per season (e.g. 7 = weekly). Leave blank to auto-detect." },
  ],
  cusum: [
    { name: "k", label: "Slack (k)", type: "number", default: 0.5, min: 0, step: 0.1, hint: "Allowance; smaller = more sensitive to drift." },
    { name: "h", label: "Threshold (h)", type: "number", default: 5.0, min: 0, step: 0.5, hint: "Decision boundary; smaller = more false positives." },
  ],
  page_hinkley: [
    { name: "delta", label: "Min change (delta)", type: "number", default: 0.005, min: 0, step: 0.001 },
    { name: "lambda_", label: "Alarm threshold (lambda)", type: "number", default: 100.0, min: 0 },
  ],
  holt_winters: [
    { name: "period", label: "Season length", type: "integer", default: 7, min: 2 },
    { name: "alpha", label: "Smoothing (alpha)", type: "number", default: 0.99, min: 0, max: 1, step: 0.01 },
  ],
  prophet_anomaly: [
    { name: "interval_width", label: "Prediction interval width", type: "number", default: 0.95, min: 0.01, max: 0.9999, step: 0.01, hint: "0.95 → Z=1.96; 0.99 → Z=2.58." },
    { name: "period", label: "Season length", type: "integer", min: 2, placeholder: "auto", hint: "Observations per season. Leave blank to auto-detect." },
  ],
  adwin: [
    { name: "delta", label: "Confidence (delta)", type: "number", default: 0.002, min: 0, step: 0.001, hint: "Smaller = more sensitive." },
  ],
  bocpd: [
    { name: "hazard_lambda", label: "Hazard lambda", type: "number", default: 50, min: 1, hint: "Expected run length between changepoints. Smaller = more sensitive." },
  ],
  matrix_profile: [
    { name: "window", label: "Subsequence window", type: "integer", default: 7, min: 2 },
  ],
};

// Default warn/fail thresholds from STAT_SCALES — shown as placeholder when not explicitly set.
const SCALE_DEFAULTS: Record<string, { warn: number; fail: number }> = {
  completeness:                  { warn: 0.95,  fail: 0.90 },
  null_fraction:                 { warn: 0.01,  fail: 0.05 },
  uniqueness:                    { warn: 0.95,  fail: 0.80 },
  validity:                      { warn: 0.95,  fail: 0.90 },
  volume:                        { warn: 0.10,  fail: 0.25 },
  volume_anomaly:                { warn: 0.5,   fail: 0.5  },
  schema_change:                 { warn: 0.5,   fail: 0.5  },
  row_count_in_range:            { warn: 0.5,   fail: 0.5  },
  max_in_range:                  { warn: 0.5,   fail: 0.5  },
  min_in_range:                  { warn: 0.5,   fail: 0.5  },
  median_in_range:               { warn: 0.5,   fail: 0.5  },
  stddev_in_range:               { warn: 0.5,   fail: 0.5  },
  sum_in_range:                  { warn: 0.5,   fail: 0.5  },
  cardinality_in_range:          { warn: 0.5,   fail: 0.5  },
  quantile_in_range:             { warn: 0.5,   fail: 0.5  },
  value_in_range:                { warn: 0.001, fail: 0.01 },
  set_membership:                { warn: 0.001, fail: 0.01 },
  set_exclusion:                 { warn: 0.001, fail: 0.01 },
  regex_match:                   { warn: 0.001, fail: 0.01 },
  string_length_range:           { warn: 0.001, fail: 0.01 },
  date_format:                   { warn: 0.001, fail: 0.01 },
  string_case:                   { warn: 0.001, fail: 0.01 },
  sql_assertion:                 { warn: 0.001, fail: 0.01 },
  column_pair:                   { warn: 0.001, fail: 0.01 },
  composite_uniqueness:          { warn: 0.001, fail: 0.01 },
  monotonicity:                  { warn: 0.5,   fail: 0.5  },
  date_part_missing:             { warn: 0.01,  fail: 0.05 },
  referential_integrity_rate:    { warn: 0.99,  fail: 0.95 },
  referential_integrity:         { warn: 0.99,  fail: 0.95 },
  freshness_seconds_behind:      { warn: 3600,  fail: 86400 },
  ks_pvalue:                     { warn: 0.95,  fail: 0.99 },
  ks_drift:                      { warn: 0.95,  fail: 0.99 },
  wasserstein_1:                 { warn: 0.20,  fail: 0.50 },
  psi:                           { warn: 0.10,  fail: 0.20 },
  kl_divergence:                 { warn: 0.10,  fail: 0.30 },
  js_divergence:                 { warn: 0.10,  fail: 0.20 },
  chi_square_drift:              { warn: 0.95,  fail: 0.99 },
  cramers_v:                     { warn: 0.15,  fail: 0.30 },
  benford_law_fit:               { warn: 0.95,  fail: 0.99 },
  mmd:                           { warn: 0.10,  fail: 0.20 },
  mutual_information:            { warn: 0.50,  fail: 0.30 },
  mad_outlier_fraction:          { warn: 0.01,  fail: 0.05 },
  double_mad_outlier_fraction:   { warn: 0.01,  fail: 0.05 },
  zscore_outlier_fraction:       { warn: 0.01,  fail: 0.05 },
  adjusted_boxplot_fraction:     { warn: 0.01,  fail: 0.05 },
  iqr_fence:                     { warn: 0.01,  fail: 0.05 },
  grubbs:                        { warn: 0.95,  fail: 0.99 },
  generalized_esd:               { warn: 0.01,  fail: 0.05 },
  outlier_fraction_drift:        { warn: 0.001, fail: 0.01 },
  isolation_forest_fraction:     { warn: 0.05,  fail: 0.10 },
  mahalanobis_distance:          { warn: 0.01,  fail: 0.05 },
  lof:                           { warn: 0.05,  fail: 0.10 },
  one_class_svm:                 { warn: 0.05,  fail: 0.10 },
  hbos:                          { warn: 0.05,  fail: 0.10 },
  ecod:                          { warn: 0.05,  fail: 0.10 },
  stl_residual_zscore:           { warn: 3.0,   fail: 5.0  },
  cusum:                         { warn: 1.0,   fail: 2.0  },
  page_hinkley:                  { warn: 0.5,   fail: 1.0  },
  holt_winters:                  { warn: 0.05,  fail: 0.10 },
  prophet_anomaly:               { warn: 0.05,  fail: 0.10 },
  adwin:                         { warn: 0.50,  fail: 0.50 },
  bocpd:                         { warn: 0.50,  fail: 0.80 },
  matrix_profile:                { warn: 0.05,  fail: 0.10 },
  callable_check:                { warn: 0.50,  fail: 0.75 },
  remote_check:                  { warn: 0.50,  fail: 0.75 },
};

// Detectors that operate on the whole table — column field is hidden in the edit form.
const TABLE_LEVEL_DETECTORS = new Set([
  "volume", "volume_anomaly", "schema_change", "row_count_in_range",
  "isolation_forest_fraction", "mahalanobis_distance", "lof", "one_class_svm", "hbos", "ecod",
]);

function coerceSchemaValue(val: string, p: ParamDef): unknown {
  if (val === "" || val === null) return undefined;
  if (p.name === "allowed_values" || p.name === "forbidden_values" || p.name === "key_columns") {
    return val.split(",").map(v => v.trim()).filter(Boolean);
  }
  if (p.type === "integer") return parseInt(val) || 0;
  if (p.type === "number") return parseFloat(val);
  return val;
}

type ValueType = "numeric" | "date" | "string";

function normalizeValueType(dbType: string): ValueType {
  const t = dbType.toLowerCase();
  if (/int|float|decimal|numeric|double|real|number/.test(t)) return "numeric";
  if (/date|time|timestamp|datetime/.test(t)) return "date";
  return "string";
}

const DATE_COL_KEYWORDS = /date|created|updated|timestamp|time|dt|at$/i;

function sortDateColumnsFirst(cols: string[]): string[] {
  return [...cols].sort((a, b) => {
    const aDate = DATE_COL_KEYWORDS.test(a);
    const bDate = DATE_COL_KEYWORDS.test(b);
    if (aDate === bDate) return a.localeCompare(b);
    return aDate ? -1 : 1;
  });
}

function ParamSchemaEditor({
  slug, values, onChange, inputCls, inputStyle, labelCls, labelStyle, columns, columnValueType, validationErrors,
}: {
  slug: string;
  values: Record<string, string>;
  onChange: (name: string, val: string) => void;
  inputCls: string;
  inputStyle: React.CSSProperties;
  labelCls: string;
  labelStyle: React.CSSProperties;
  columns?: string[];
  columnValueType?: ValueType;
  validationErrors?: Set<string>;
}) {
  const schema = DETECTOR_PARAMS[slug];
  const sortedColumns = useMemo(() => columns ? sortDateColumnsFirst(columns) : [], [columns]);

  function effectiveParamType(p: ParamDef): ParamDef["type"] {
    if (slug === "value_in_range" && (p.name === "min_value" || p.name === "max_value")) {
      if (columnValueType === "date") return "date";
      if (columnValueType === "string") return "text";
    }
    return p.type;
  }

  const warnVal = values.warn_threshold ?? "";
  const failVal = values.fail_threshold ?? "";

  return (
    <div className="space-y-3">
      {/* Detector-specific params */}
      {schema && schema.map(p => {
        const isInvalid = validationErrors?.has(p.name);
        const errorBorderStyle = isInvalid ? { borderColor: "var(--fail)" } : {};
        return (
          <label key={p.name} className="block space-y-1">
            <span className={labelCls} style={labelStyle}>
              {p.label}
              {p.required && <span style={{ color: "var(--fail)", marginLeft: 3 }}>*</span>}
            </span>
            {p.type === "column" ? (
              sortedColumns.length > 0 ? (
                <select
                  value={values[p.name] ?? ""}
                  onChange={e => onChange(p.name, e.target.value)}
                  className={inputCls}
                  style={{ ...inputStyle, ...errorBorderStyle }}
                >
                  <option value="">-- select column --</option>
                  {sortedColumns.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              ) : (
                <input
                  type="text"
                  className={inputCls}
                  style={{ ...inputStyle, ...errorBorderStyle }}
                  value={values[p.name] ?? ""}
                  onChange={e => onChange(p.name, e.target.value)}
                  placeholder={p.placeholder ?? ""}
                />
              )
            ) : p.selectOptions ? (
              <select value={values[p.name] ?? String(p.default ?? "")} onChange={e => onChange(p.name, e.target.value)} className={inputCls} style={{ ...inputStyle, ...errorBorderStyle }}>
                {p.selectOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            ) : (() => {
              const et = effectiveParamType(p);
              return (
                <input
                  type={et === "number" || et === "integer" ? "number" : et === "date" ? "date" : "text"}
                  className={inputCls}
                  style={{ ...inputStyle, ...errorBorderStyle }}
                  value={values[p.name] ?? ""}
                  onChange={e => onChange(p.name, e.target.value)}
                  placeholder={et === "date" ? "yyyy-mm-dd" : (p.placeholder ?? (p.default !== null && p.default !== undefined ? String(p.default) : ""))}
                  min={et === "number" || et === "integer" ? p.min : undefined}
                  max={et === "number" || et === "integer" ? p.max : undefined}
                  step={et === "number" || et === "integer" ? (p.step ?? (et === "integer" ? 1 : undefined)) : undefined}
                />
              );
            })()}
            {p.hint && <p className="t-micro" style={{ color: "var(--fg-3)" }}>{p.hint}</p>}
          </label>
        );
      })}

      {/* Unknown detector: fallback key-value display */}
      {!schema && Object.entries(values).filter(([k]) => k !== "warn_threshold" && k !== "fail_threshold").map(([k, v]) => (
        <div key={k} className="flex items-center gap-1.5">
          <span className="t-micro font-mono flex-shrink-0" style={{ color: "var(--fg-2)", width: 140 }}>{k}</span>
          <span className="t-micro" style={{ color: "var(--fg-3)" }}>:</span>
          <input
            value={v}
            onChange={e => onChange(k, e.target.value)}
            className="flex-1 px-2 py-1 border border-line t-small outline-none font-mono"
            style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
          />
        </div>
      ))}

      {/* Thresholds */}
      {(() => {
        const scaleDefaults = SCALE_DEFAULTS[slug];
        const warnInvalid = validationErrors?.has("warn_threshold");
        const failInvalid = validationErrors?.has("fail_threshold");
        return (
          <div className="grid grid-cols-2 gap-3">
            <label className="block space-y-1">
              <span className={labelCls} style={{ ...labelStyle, color: "var(--warn)" }}>
                Warn threshold<span style={{ color: "var(--fail)", marginLeft: 3 }}>*</span>
              </span>
              <input type="number" step="any" className={inputCls}
                style={{ ...inputStyle, color: "var(--warn)", ...(warnInvalid ? { borderColor: "var(--fail)" } : {}) }}
                value={warnVal} onChange={e => onChange("warn_threshold", e.target.value)}
                placeholder={scaleDefaults ? String(scaleDefaults.warn) : ""} />
            </label>
            <label className="block space-y-1">
              <span className={labelCls} style={{ ...labelStyle, color: "var(--fail)" }}>
                Fail threshold<span style={{ color: "var(--fail)", marginLeft: 3 }}>*</span>
              </span>
              <input type="number" step="any" className={inputCls}
                style={{ ...inputStyle, color: "var(--fail)", ...(failInvalid ? { borderColor: "var(--fail)" } : {}) }}
                value={failVal} onChange={e => onChange("fail_threshold", e.target.value)}
                placeholder={scaleDefaults ? String(scaleDefaults.fail) : ""} />
            </label>
          </div>
        );
      })()}
    </div>
  );
}

function ImportYamlModal({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [mode, setMode] = useState<"merge" | "replace">("merge");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<{ added: number; skipped: number; deleted: number; errors: string[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleImport() {
    if (!file) return;
    setStatus("loading");
    try {
      const yaml_content = await file.text();
      const res = await fetch("/api/v1/checks/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml_content, mode }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Import failed");
      setResult(data);
      setStatus("done");
      onImported();
    } catch (err) {
      setResult({ added: 0, skipped: 0, deleted: 0, errors: [String(err)] });
      setStatus("error");
    }
  }

  const inputStyle = { background: "var(--bg-2)", color: "var(--fg-0)" };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.55)" }}>
      <div className="border border-line" style={{ background: "var(--bg-1)", width: 440 }}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="t-h3" style={{ color: "var(--fg-0)" }}>Import YAML</span>
          <button onClick={onClose} className="flex items-center justify-center w-6 h-6 border border-line hover:opacity-70 transition-colors" style={{ color: "var(--fg-2)" }}><X size={12} strokeWidth={1.6} /></button>
        </div>

        <div className="p-4 space-y-4">
          {/* File picker */}
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>YAML file</p>
            <input ref={fileRef} type="file" accept=".yaml,.yml" className="hidden" onChange={e => setFile(e.target.files?.[0] ?? null)} />
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full px-3 py-2 border border-line t-small text-left flex items-center gap-2 hover:opacity-80 transition-colors"
              style={inputStyle}
            >
              <Upload size={13} strokeWidth={1.6} style={{ color: "var(--fg-3)", flexShrink: 0 }} />
              <span style={{ color: file ? "var(--fg-0)" : "var(--fg-3)" }}>
                {file ? file.name : "Choose a .yaml file..."}
              </span>
            </button>
          </div>

          {/* Mode selection */}
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Import mode</p>
            <div className="space-y-2">
              {([
                { value: "merge",   label: "Add checks", desc: "Append imported checks — skip any that already exist (matched by table + column + detector)." },
                { value: "replace", label: "Replace all", desc: "Delete every existing check, then add the imported ones. Deduplicated within the file." },
              ] as const).map(opt => (
                <label key={opt.value} className="flex items-start gap-2.5 cursor-pointer group" onClick={() => setMode(opt.value)}>
                  <div className="mt-0.5 w-3.5 h-3.5 border flex-shrink-0 flex items-center justify-center transition-colors"
                    style={{ borderColor: mode === opt.value ? "var(--accent)" : "var(--line)", background: mode === opt.value ? "var(--accent)" : "transparent" }}>
                    {mode === opt.value && <div className="w-1.5 h-1.5" style={{ background: "var(--bg-0)" }} />}
                  </div>
                  <div>
                    <p className="t-small" style={{ color: "var(--fg-0)" }}>{opt.label}</p>
                    <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Result */}
          {status === "done" && result && (
            <div className="px-3 py-2 border border-line t-small space-y-1" style={{ background: "var(--bg-2)", color: "var(--fg-1)" }}>
              <p style={{ color: "var(--pass)" }}>Import complete</p>
              <p>Added: <strong>{result.added}</strong> &nbsp; Skipped: <strong>{result.skipped}</strong>
                {result.deleted > 0 && <> &nbsp; Deleted: <strong>{result.deleted}</strong></>}
              </p>
              {result.errors.length > 0 && (
                <p style={{ color: "var(--warn)" }}>{result.errors.length} warning{result.errors.length > 1 ? "s" : ""}: {result.errors[0]}</p>
              )}
            </div>
          )}
          {status === "error" && result && (
            <div className="px-3 py-2 border t-small" style={{ background: "var(--bg-2)", borderColor: "var(--fail)", color: "var(--fail)" }}>
              {result.errors[0]}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 px-4 py-3 border-t border-line">
          <button onClick={onClose} className="px-3 py-1.5 border border-line t-small hover:opacity-80 transition-colors" style={{ color: "var(--fg-1)" }}>
            {status === "done" ? "Close" : "Cancel"}
          </button>
          {status !== "done" && (
            <button
              onClick={handleImport}
              disabled={!file || status === "loading"}
              className="px-3 py-1.5 border t-small flex items-center gap-1.5 hover:opacity-80 transition-colors disabled:opacity-40"
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
            >
              {status === "loading" ? <Loader2 size={12} strokeWidth={1.6} className="animate-spin" /> : <Upload size={12} strokeWidth={1.6} />}
              {status === "loading" ? "Importing..." : "Import"}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

function CheckEditModal({ check, onClose, onSave }: { check: CheckRow; onClose: () => void; onSave: (u: CheckRow) => void }) {
  const [dataset, setDataset] = useState(check.dataset);
  const [column, setColumn] = useState(check.column);
  const [detector, setDetector] = useState(check.check);
  const [enabled, setEnabled] = useState(check.enabled);
  const [saving, setSaving] = useState(false);
  const [editColMeta, setEditColMeta] = useState<{ name: string; data_type: string }[]>([]);
  const editColumns = useMemo(() => editColMeta.map(c => c.name), [editColMeta]);

  useEffect(() => {
    if (!check.dataset) return;
    fetch(`/api/v1/datasets/${encodeURIComponent(check.dataset)}/columns`)
      .then(r => r.ok ? r.json() : [])
      .then((cols: { name: string; data_type: string }[]) => setEditColMeta(cols))
      .catch(() => {});
  }, [check.dataset]);

  const columnValueType: ValueType = useMemo(() => {
    const meta = editColMeta.find(c => c.name === column);
    if (meta) return normalizeValueType(meta.data_type);
    // Fall back to stored value_type if the column isn't found live
    return (check.params.value_type as ValueType | undefined) ?? "numeric";
  }, [editColMeta, column, check.params.value_type]);

  const isFreshness = detector === "freshness_seconds_behind";

  const [validationErrors, setValidationErrors] = useState<Set<string>>(new Set());

  // All non-freshness params (including thresholds) stored as string values
  const [paramValues, setParamValues] = useState<Record<string, string>>(() => {
    const schema = DETECTOR_PARAMS[check.check];
    const result: Record<string, string> = {};
    if (schema) {
      schema.forEach(p => {
        if (p.default !== null && p.default !== undefined) result[p.name] = String(p.default);
      });
    }
    Object.entries(check.params).forEach(([k, v]) => {
      if (v !== null && v !== undefined) result[k] = String(v);
    });
    // Pre-fill thresholds from SCALE_DEFAULTS when not already set in stored params
    const scaleDefaults = SCALE_DEFAULTS[check.check];
    if (scaleDefaults) {
      if (!result.warn_threshold) result.warn_threshold = String(scaleDefaults.warn);
      if (!result.fail_threshold) result.fail_threshold = String(scaleDefaults.fail);
    }
    return result;
  });

  // Freshness: stored in seconds, displayed in selected unit
  const defaultWarnSecs = readFreshnessSecs(check.params, "warn", 86400);   // 1 day
  const defaultFailSecs = readFreshnessSecs(check.params, "fail", 604800);  // 7 days
  const [freshnessUnit, setFreshnessUnit] = useState<FreshnessUnit>(() => bestUnit(defaultWarnSecs));
  const [warnValue, setWarnValue] = useState(() => String(defaultWarnSecs / UNIT_TO_SECONDS[bestUnit(defaultWarnSecs)]));
  const [failValue, setFailValue] = useState(() => String(defaultFailSecs / UNIT_TO_SECONDS[bestUnit(defaultWarnSecs)]));

  const warnSecs = Math.round(parseFloat(warnValue || "0") * UNIT_TO_SECONDS[freshnessUnit]);
  const failSecs = Math.round(parseFloat(failValue || "0") * UNIT_TO_SECONDS[freshnessUnit]);

  function changeUnit(u: FreshnessUnit) {
    const prevMult = UNIT_TO_SECONDS[freshnessUnit];
    const nextMult = UNIT_TO_SECONDS[u];
    setWarnValue(String((parseFloat(warnValue || "0") * prevMult) / nextMult));
    setFailValue(String((parseFloat(failValue || "0") * prevMult) / nextMult));
    setFreshnessUnit(u);
  }

  function buildParams(): Record<string, unknown> {
    if (isFreshness) return { warn_seconds: warnSecs, fail_seconds: failSecs };
    const schema = DETECTOR_PARAMS[detector];
    const result: Record<string, unknown> = {};
    Object.entries(paramValues).forEach(([k, v]) => {
      if (v === "" || v === null || k === "value_type") return;
      // For value_in_range on non-numeric columns keep bound values as strings
      if (detector === "value_in_range" && columnValueType !== "numeric" && (k === "min_value" || k === "max_value")) {
        result[k] = v;
        return;
      }
      const pDef = schema?.find(p => p.name === k);
      result[k] = pDef ? (coerceSchemaValue(v, pDef) ?? v) : coerceParamValue(v);
    });
    if (detector === "value_in_range") result.value_type = columnValueType;
    return result;
  }

  async function handleSave() {
    if (!isFreshness) {
      const errors = new Set<string>();
      const schema = DETECTOR_PARAMS[detector];
      schema?.forEach(p => {
        if (p.required && !paramValues[p.name]?.trim()) errors.add(p.name);
      });
      if (!paramValues.warn_threshold?.trim()) errors.add("warn_threshold");
      if (!paramValues.fail_threshold?.trim()) errors.add("fail_threshold");
      if (errors.size > 0) {
        setValidationErrors(errors);
        return;
      }
      setValidationErrors(new Set());
    }
    setSaving(true);
    const params = buildParams();
    await fetch(`/api/v1/checks/${check.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ params, enabled }),
    }).catch(() => null);
    setSaving(false);
    onSave({ ...check, dataset, column, check: detector, params, enabled });
    onClose();
  }

  const inputCls = "w-full px-3 py-1.5 border border-line t-small outline-none font-mono";
  const inputStyle = { background: "var(--bg-2)", color: "var(--fg-0)" };
  const labelCls = "t-micro";
  const labelStyle = { color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" as const };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.55)" }}>
      <div className="border border-line" style={{ background: "var(--bg-1)", width: 480, maxHeight: "90vh", overflow: "auto" }}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="t-h3" style={{ color: "var(--fg-0)" }}>Edit Check</span>
          <button onClick={onClose} className="flex items-center justify-center w-6 h-6 border border-line hover:bg-bg-2 transition-colors" style={{ color: "var(--fg-2)" }}><X size={12} strokeWidth={1.6} /></button>
        </div>
        <div className="p-4 space-y-4">
          {/* Common fields */}
          {([["Detector", detector, setDetector], ["Dataset", dataset, setDataset]] as [string, string, (v: string) => void][]).map(([lbl, val, setter]) => (
            <label key={lbl} className="block space-y-1">
              <span className={labelCls} style={labelStyle}>{lbl}</span>
              <input className={inputCls} style={inputStyle} value={val} onChange={e => setter(e.target.value)} />
            </label>
          ))}
          {!TABLE_LEVEL_DETECTORS.has(detector) && (
            <label className="block space-y-1">
              <span className={labelCls} style={labelStyle}>Column</span>
              <input className={inputCls} style={inputStyle} value={column} onChange={e => setColumn(e.target.value)} />
            </label>
          )}

          {/* Freshness thresholds */}
          {isFreshness && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className={labelCls} style={labelStyle}>Freshness thresholds</span>
                <div className="flex gap-0.5">
                  {(["seconds", "minutes", "hours", "days"] as FreshnessUnit[]).map(u => (
                    <button key={u} onClick={() => changeUnit(u)} className="px-2 py-0.5 t-micro border transition-colors capitalize" style={{ borderColor: freshnessUnit === u ? "var(--accent)" : "var(--line)", color: freshnessUnit === u ? "var(--accent)" : "var(--fg-2)", background: freshnessUnit === u ? "var(--accent-bg)" : "var(--bg-2)" }}>
                      {u}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="block space-y-1">
                  <span className={labelCls} style={{ ...labelStyle, color: "var(--warn)" }}>Warn after</span>
                  <div className="flex items-center gap-1.5">
                    <input type="number" min="0" step="1" className={inputCls} style={{ ...inputStyle, color: "var(--warn)" }} value={warnValue} onChange={e => setWarnValue(e.target.value)} />
                    <span className="t-micro flex-shrink-0" style={{ color: "var(--fg-3)" }}>{freshnessUnit}</span>
                  </div>
                </label>
                <label className="block space-y-1">
                  <span className={labelCls} style={{ ...labelStyle, color: "var(--fail)" }}>Fail after</span>
                  <div className="flex items-center gap-1.5">
                    <input type="number" min="0" step="1" className={inputCls} style={{ ...inputStyle, color: "var(--fail)" }} value={failValue} onChange={e => setFailValue(e.target.value)} />
                    <span className="t-micro flex-shrink-0" style={{ color: "var(--fg-3)" }}>{freshnessUnit}</span>
                  </div>
                </label>
              </div>
              <p className="t-micro" style={{ color: "var(--fg-3)" }}>
                Stored as: warn_seconds={warnSecs}, fail_seconds={failSecs}
              </p>
            </div>
          )}

          {/* Schema-driven params for non-freshness checks */}
          {!isFreshness && (
            <ParamSchemaEditor
              slug={detector}
              values={paramValues}
              onChange={(name, val) => {
                setParamValues(prev => ({ ...prev, [name]: val }));
                setValidationErrors(prev => { const next = new Set(prev); next.delete(name); return next; });
              }}
              inputCls={inputCls}
              inputStyle={inputStyle}
              labelCls={labelCls}
              labelStyle={labelStyle}
              columns={editColumns}
              columnValueType={columnValueType}
              validationErrors={validationErrors}
            />
          )}

          <div className="flex items-center justify-between py-1">
            <span className="t-small" style={{ color: "var(--fg-1)" }}>Enabled</span>
            <button onClick={() => setEnabled(v => !v)} className="relative border transition-colors" style={{ width: 36, height: 20, background: enabled ? "var(--accent)" : "var(--bg-2)", borderColor: enabled ? "var(--accent)" : "var(--line)" }}>
              <span style={{ position: "absolute", top: 2, left: enabled ? 18 : 2, width: 14, height: 14, background: enabled ? "var(--bg-0)" : "var(--fg-3)", transition: "left 0.15s" }} />
            </button>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-line">
          <button onClick={onClose} disabled={saving} className="px-3 py-1.5 t-small border border-line hover:bg-bg-2 transition-colors disabled:opacity-40" style={{ color: "var(--fg-1)" }}>Cancel</button>
          <button onClick={handleSave} disabled={saving} className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-90 disabled:opacity-60" style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}>
            {saving && <Loader2 size={11} strokeWidth={2} className="animate-spin" />}
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Searchable select (custom dropdown with filter input)
// ---------------------------------------------------------------------------

interface SelectOption { value: string; label: string; sublabel?: string; }

function SearchSelect({
  options, value, onChange, placeholder = "Select...", disabled = false,
}: {
  options: SelectOption[];
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (open) searchRef.current?.focus(); }, [open]);
  useEffect(() => { if (!open) setSearch(""); }, [open]);

  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") setOpen(false); }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, []);

  const q = search.toLowerCase();
  const filtered = options.filter(o =>
    o.label.toLowerCase().includes(q) || o.value.toLowerCase().includes(q) || (o.sublabel ?? "").toLowerCase().includes(q)
  );
  const selectedLabel = options.find(o => o.value === value)?.label ?? value;

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen(v => !v)}
        className="w-full px-3 py-1.5 border border-line t-small text-left flex items-center justify-between gap-2 transition-colors"
        style={{
          background: "var(--bg-2)",
          color: value ? "var(--fg-0)" : "var(--fg-3)",
          borderColor: open ? "var(--accent)" : "var(--line)",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.45 : 1,
        }}
      >
        <span className="truncate font-mono" style={{ fontSize: 12 }}>{value ? selectedLabel : placeholder}</span>
        <ChevronDown size={11} strokeWidth={1.6} style={{ flexShrink: 0, color: "var(--fg-3)", transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s" }} />
      </button>
      {open && (
        <div style={{ position: "absolute", top: "calc(100% + 2px)", left: 0, right: 0, zIndex: 200, background: "var(--bg-1)", border: "1px solid var(--accent)", boxShadow: "0 4px 16px rgba(0,0,0,0.35)" }}>
          <div style={{ padding: "6px 6px 5px" }}>
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search..."
              className="w-full px-2 py-1 t-small outline-none"
              style={{ background: "var(--bg-2)", color: "var(--fg-0)", border: "1px solid var(--line)" }}
            />
          </div>
          <div style={{ maxHeight: 200, overflowY: "auto", borderTop: "1px solid var(--line)" }}>
            {filtered.length === 0 ? (
              <p className="px-3 py-2 t-micro" style={{ color: "var(--fg-3)" }}>No matches</p>
            ) : filtered.map(o => (
              <button
                key={o.value}
                type="button"
                onClick={() => { onChange(o.value); setOpen(false); }}
                className="w-full px-3 py-1.5 t-small text-left flex items-center justify-between gap-2"
                style={{
                  background: o.value === value ? "var(--accent-bg)" : "transparent",
                  color: o.value === value ? "var(--accent)" : "var(--fg-0)",
                }}
                onMouseEnter={e => { if (o.value !== value) (e.currentTarget as HTMLElement).style.background = "var(--bg-2)"; }}
                onMouseLeave={e => { if (o.value !== value) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
              >
                <span className="truncate font-mono" style={{ fontSize: 12 }}>{o.label}</span>
                {o.sublabel && <span className="t-micro flex-shrink-0" style={{ color: "var(--fg-3)" }}>{o.sublabel}</span>}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Add Check panel
// ---------------------------------------------------------------------------

function AddCheckPanel({ checks, onAdded }: {
  checks: CheckRow[];
  onAdded: (chk: CheckRow) => void;
}) {
  const [detectors, setDetectors] = useState<{ slug: string; label: string; group: string; params: Record<string, unknown> }[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [column, setColumn] = useState("");
  const [detectorSlug, setDetectorSlug] = useState("");
  const [paramValues, setParamValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState(false);

  useEffect(() => {
    fetch("/api/v1/detectors")
      .then(r => r.ok ? r.json() : [])
      .then(setDetectors)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const det = detectors.find(d => d.slug === detectorSlug);
    const schema = DETECTOR_PARAMS[detectorSlug];
    const result: Record<string, string> = {};
    if (schema) {
      schema.forEach(p => {
        if (p.default !== null && p.default !== undefined) result[p.name] = String(p.default);
      });
    }
    if (det) {
      Object.entries(det.params).forEach(([k, v]) => {
        if (v !== null && v !== undefined) result[k] = String(v);
      });
    }
    setParamValues(result);
  }, [detectorSlug, detectors]);

  const [liveColumns, setLiveColumns] = useState<string[]>([]);
  const [columnsLoading, setColumnsLoading] = useState(false);

  useEffect(() => {
    if (!datasetId) { setLiveColumns([]); return; }
    setColumnsLoading(true);
    fetch(`/api/v1/datasets/${encodeURIComponent(datasetId)}/columns`)
      .then(r => r.ok ? r.json() : [])
      .then((cols: { name: string }[]) => setLiveColumns(cols.map(c => c.name).sort()))
      .catch(() => setLiveColumns([]))
      .finally(() => setColumnsLoading(false));
  }, [datasetId]);

  const datasetOptions = useMemo<SelectOption[]>(
    () => Array.from(new Set(checks.map(c => c.dataset))).sort().map(d => ({ value: d, label: d })),
    [checks]
  );
  const columnOptions = useMemo<SelectOption[]>(
    () => (liveColumns.length > 0 ? liveColumns : Array.from(new Set(checks.filter(c => c.dataset === datasetId).map(c => c.column))).sort()).map(c => ({ value: c, label: c })),
    [liveColumns, checks, datasetId]
  );
  const detectorOptions = useMemo<SelectOption[]>(
    () => detectors.map(d => ({ value: d.slug, label: d.label, sublabel: d.group })),
    [detectors]
  );

  const canSave = datasetId !== "" && column !== "" && detectorSlug !== "";

  async function handleAdd() {
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      const schema = DETECTOR_PARAMS[detectorSlug];
      const params: Record<string, unknown> = {};
      Object.entries(paramValues).forEach(([k, v]) => {
        if (v === "" || v === null) return;
        const pDef = schema?.find(p => p.name === k);
        params[k] = pDef ? (coerceSchemaValue(v, pDef) ?? v) : coerceParamValue(v);
      });
      const res = await fetch(
        `/api/v1/datasets/${encodeURIComponent(datasetId)}/columns/${encodeURIComponent(column)}/checks`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ detector_slug: detectorSlug, params, rationale: "" }),
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({})) as { detail?: string };
        setError(data.detail ?? "Failed to add check");
        return;
      }
      const data = await res.json() as { id: string; dataset_id: string; column: string; detector_slug: string; params: Record<string, unknown>; enabled: boolean };
      onAdded({
        id: data.id,
        group: DETECTOR_GROUP[data.detector_slug] ?? "custom",
        dataset: data.dataset_id,
        column: data.column,
        check: data.detector_slug,
        score: null,
        verdict: "pending",
        params: data.params ?? {},
        enabled: data.enabled !== false,
        plain_english: null,
        ran_at: null,
      });
      setColumn("");
      setDetectorSlug("");
      setParamValues({});
      setAdded(true);
      setTimeout(() => setAdded(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  const labelStyle: React.CSSProperties = { color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" };

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full">
      <span className="t-h3" style={{ color: "var(--fg-0)" }}>Add a Check</span>

      <div className="space-y-1">
        <span className="t-micro" style={labelStyle}>Dataset</span>
        <SearchSelect
          options={datasetOptions}
          value={datasetId}
          onChange={v => { setDatasetId(v); setColumn(""); }}
          placeholder="schema.table"
        />
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="t-micro" style={labelStyle}>Column</span>
          {columnsLoading && <Loader2 size={10} strokeWidth={2} className="animate-spin" style={{ color: "var(--fg-3)" }} />}
        </div>
        <SearchSelect
          options={columnOptions}
          value={column}
          onChange={setColumn}
          placeholder={columnsLoading ? "Loading columns..." : "column_name"}
          disabled={!datasetId || columnsLoading}
        />
      </div>

      <div className="space-y-1">
        <span className="t-micro" style={labelStyle}>Check type</span>
        <SearchSelect
          options={detectorOptions}
          value={detectorSlug}
          onChange={setDetectorSlug}
          placeholder="Select check type"
        />
      </div>

      {detectorSlug && (
        <ParamSchemaEditor
          slug={detectorSlug}
          values={paramValues}
          onChange={(name, val) => setParamValues(prev => ({ ...prev, [name]: val }))}
          inputCls="w-full px-3 py-1.5 border border-line t-small outline-none font-mono"
          inputStyle={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
          labelCls="t-micro"
          labelStyle={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" as const }}
          columns={liveColumns}
        />
      )}

      {error && (
        <div className="px-3 py-2 t-small border" style={{ background: "var(--fail-bg)", borderColor: "var(--fail)", color: "var(--fail)" }}>
          {error}
        </div>
      )}

      <button
        onClick={handleAdd}
        disabled={saving || !canSave}
        className="flex items-center gap-2 px-4 py-1.5 t-small border transition-colors hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        style={{
          background: added ? "var(--pass)" : "var(--accent)",
          color: "var(--bg-0)",
          borderColor: added ? "var(--pass)" : "var(--accent)",
        }}
      >
        {saving && <Loader2 size={12} strokeWidth={2} className="animate-spin" />}
        {added ? "Added!" : "Add Check"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// KS drift window helper
// ---------------------------------------------------------------------------

function computeKsDriftWindows(params: Record<string, unknown>): { reference: string; current: string; dateCol: string } | null {
  const dateCol = String(params.date_col ?? "").trim();
  const referenceDays = Number(params.reference_days ?? 30);
  const currentDays = Number(params.current_days ?? 7);
  if (!dateCol || isNaN(referenceDays) || isNaN(currentDays) || referenceDays < 1 || currentDays < 1) return null;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const currStart = new Date(today);
  currStart.setDate(today.getDate() - (currentDays - 1));

  const refEnd = new Date(currStart);
  refEnd.setDate(currStart.getDate() - 1);

  const refStart = new Date(refEnd);
  refStart.setDate(refEnd.getDate() - (referenceDays - 1));

  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return {
    dateCol,
    reference: `${fmt(refStart)} to ${fmt(refEnd)} (${referenceDays}d)`,
    current: `${fmt(currStart)} to ${fmt(today)} (${currentDays}d)`,
  };
}

// ---------------------------------------------------------------------------
// Right panel
// ---------------------------------------------------------------------------

function RightPanel({ selectedCheckId, checks, onEditCheck, onRunSingle, runningIds, onCheckAdded }: {
  selectedCheckId: string | null;
  checks: CheckRow[];
  onEditCheck: (id: string) => void;
  onRunSingle: (e: React.MouseEvent, id: string) => void;
  runningIds: Set<string>;
  onCheckAdded: (chk: CheckRow) => void;
}) {
  const [sql, setSql] = useState<string | null>(null);
  const [sqlLoading, setSqlLoading] = useState(false);
  const [sqlError, setSqlError] = useState<string | null>(null);

  // Serialize the selected check's params so the SQL re-fetches whenever they change after a save.
  const selectedParamsKey = JSON.stringify(
    checks.find(c => c.id === selectedCheckId)?.params ?? {}
  );

  useEffect(() => {
    if (!selectedCheckId) { setSql(null); setSqlError(null); return; }
    setSql(null); setSqlError(null); setSqlLoading(true);
    fetch(`/api/v1/checks/${selectedCheckId}/sql`)
      .then(r => {
        if (!r.ok) return r.json().then((b: { detail?: string }) => Promise.reject(b?.detail ?? "SQL unavailable"));
        return r.json();
      })
      .then(({ sql: s }: { sql: string }) => setSql(s))
      .catch((err: unknown) => setSqlError(typeof err === "string" ? err : "SQL not available for this check type."))
      .finally(() => setSqlLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCheckId, selectedParamsKey]);

  function downloadSqlContent(chk: CheckRow) {
    if (!sql) return;
    const blob = new Blob([sql], { type: "text/sql" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${chk.check}-${chk.column}.sql`; a.click();
    URL.revokeObjectURL(url);
  }

  if (selectedCheckId) {
    const chk = checks.find(c => c.id === selectedCheckId);
    if (!chk) return null;
    const yaml = checkToYaml(chk);
    return (
      <div className="p-4 space-y-3">
        {/* Toolbar — above check name */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={e => onRunSingle(e, chk.id)}
            disabled={runningIds.has(chk.id)}
            className="px-2.5 py-1 t-micro border border-line hover:border-accent transition-colors flex items-center gap-1 disabled:opacity-40"
            style={{ color: "var(--fg-1)" }}
          >
            {runningIds.has(chk.id)
              ? <Loader2 size={11} strokeWidth={1.6} className="animate-spin" />
              : <Play size={11} strokeWidth={1.6} />}
            Run
          </button>
          <button
            onClick={() => downloadYaml(`${chk.check}-${chk.column}.yaml`, yaml)}
            className="px-2.5 py-1 t-micro border border-line hover:border-accent transition-colors flex items-center gap-1"
            style={{ color: "var(--fg-1)" }}
          >
            <Download size={11} strokeWidth={1.6} /> YAML
          </button>
          <button
            onClick={() => downloadSqlContent(chk)}
            disabled={!sql}
            className="px-2.5 py-1 t-micro border border-line hover:border-accent transition-colors flex items-center gap-1 disabled:opacity-40"
            style={{ color: "var(--fg-1)" }}
          >
            <Download size={11} strokeWidth={1.6} /> SQL
          </button>
          <button
            onClick={() => onEditCheck(chk.id)}
            className="inline-flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors"
            style={{ color: "var(--fg-3)" }}
            title="Edit check"
          >
            <Pencil size={11} strokeWidth={1.6} />
          </button>
        </div>

        {/* Check identity */}
        <div>
          <p className="t-h3" style={{ color: "var(--fg-0)" }}>{chk.check}</p>
          <p className="t-small font-mono mt-0.5" style={{ color: "var(--fg-1)" }}>{chk.dataset}.{chk.column}</p>
        </div>

        {chk.verdict === "error" && chk.plain_english && (
          <div className="px-3 py-2 t-small border" style={{ background: "var(--fail-bg)", borderColor: "var(--fail)", color: "var(--fail)" }}>
            {chk.plain_english}
          </div>
        )}

        <div>
          <p className="t-micro mb-1.5" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Check definition</p>
          <CodeBlock code={yaml} language="yaml" />
        </div>

        <div>
          <p className="t-micro mb-1.5" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Warehouse SQL</p>
          {sqlLoading && (
            <div className="px-3 py-2 t-micro" style={{ color: "var(--fg-3)" }}>Loading...</div>
          )}
          {!sqlLoading && sqlError && (
            <div className="px-3 py-2 t-small border" style={{ background: "var(--bg-2)", borderColor: "var(--line)", color: "var(--fg-2)" }}>{sqlError}</div>
          )}
          {!sqlLoading && sql && (
            <CodeBlock code={sql} language="sql" />
          )}
        </div>
      </div>
    );
  }

  return <AddCheckPanel checks={checks} onAdded={onCheckAdded} />;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const EMPTY_SET = new Set<string>();

export default function ChecksPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingCheckId, setEditingCheckId] = useState<string | null>(null);
  const [checks, setChecks] = useState<CheckRow[]>([]);
  const [loading, setLoading] = useState(true);

  // Excel-style filter state: empty Set = no filter (show all)
  const [filterSets, setFilterSets] = useState<Record<FilterKey, Set<string>>>({
    dataset_col: EMPTY_SET,
    category: EMPTY_SET,
    check: EMPTY_SET,
    verdict: EMPTY_SET,
  });
  const [openFilter, setOpenFilter] = useState<FilterKey | null>(null);

  // Refs for header cell anchors
  const headerEls = useRef<Partial<Record<FilterKey, HTMLTableCellElement | null>>>({});

  const [rightWidth, setRightWidth] = useState(400);
  const resizeDragRef = useRef<{ startX: number; startWidth: number } | null>(null);

  function onRightPanelResizeStart(e: React.MouseEvent) {
    e.preventDefault();
    resizeDragRef.current = { startX: e.clientX, startWidth: rightWidth };
    function onMove(ev: MouseEvent) {
      if (!resizeDragRef.current) return;
      const delta = resizeDragRef.current.startX - ev.clientX;
      setRightWidth(Math.max(280, Math.min(800, resizeDragRef.current.startWidth + delta)));
    }
    function onUp() {
      resizeDragRef.current = null;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [lastRunAt, setLastRunAt] = useState<string | null>(null);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [runningElapsed, setRunningElapsed] = useState(0);
  const [runDone, setRunDone] = useState(false);
  const [runningIds, setRunningIds] = useState<Set<string>>(new Set());

  // Gmail-style multiselect
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const lastCheckedIdxRef = useRef<number>(-1);

  // Delete confirmation state
  const [deleteSingleConfirmId, setDeleteSingleConfirmId] = useState<string | null>(null);
  const [deleteAllConfirm, setDeleteAllConfirm] = useState(false);
  const [deleteSelectedConfirm, setDeleteSelectedConfirm] = useState(false);

  const loadSchedules = useCallback(async () => {
    const res = await fetch("/api/v1/schedules").catch(() => null);
    if (res?.ok) {
      const data = await res.json();
      setSchedules(data.schedules ?? []);
      setLastRunAt(data.last_run_at ?? null);
    }
  }, []);

  useEffect(() => {
    fetch("/api/v1/checks")
      .then(r => r.ok ? r.json() : [])
      .then((data: unknown[]) => setChecks((data as Parameters<typeof apiToRow>[0][]).map(apiToRow)))
      .catch(() => setChecks([]))
      .finally(() => setLoading(false));
    loadSchedules();
  }, [loadSchedules]);

  async function handleRunNow() {
    setRunning(true);
    setRunDone(false);
    setRunningElapsed(0);
    const startedAt = Date.now();

    // Mark every enabled check as in-progress immediately
    const enabledIds = new Set(checks.filter(c => c.enabled).map(c => c.id));
    setRunningIds(enabledIds);

    // Snapshot of ran_at so we can detect when each check finishes
    const lastRanAt = new Map(checks.map(c => [c.id, c.ran_at]));

    const ticker = setInterval(() => {
      setRunningElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    try {
      await fetch("/api/v1/checks/refresh", { method: "POST" });

      // Poll until the backend reports the run is finished (max 3 min)
      for (let i = 0; i < 90; i++) {
        await new Promise(r => setTimeout(r, 2000));
        const [statusRes, checksRes] = await Promise.all([
          fetch("/api/v1/checks/running"),
          fetch("/api/v1/checks"),
        ]);
        if (checksRes.ok) {
          const data = await checksRes.json() as Parameters<typeof apiToRow>[0][];
          const updated = data.map(apiToRow);
          setChecks(updated);

          // Clear spinner for checks whose ran_at changed (they finished)
          const justDone = updated
            .filter(c => enabledIds.has(c.id) && c.ran_at !== lastRanAt.get(c.id))
            .map(c => c.id);
          if (justDone.length > 0) {
            for (const id of justDone) {
              const chk = updated.find(c => c.id === id);
              if (chk) lastRanAt.set(id, chk.ran_at);
            }
            setRunningIds(prev => {
              const next = new Set(prev);
              for (const id of justDone) next.delete(id);
              return next;
            });
          }
        }
        if (statusRes.ok) {
          const { running: stillRunning } = await statusRes.json() as { running: boolean };
          if (!stillRunning) break;
        }
      }

      await loadSchedules();
      setRunDone(true);
      setTimeout(() => setRunDone(false), 3000);
    } finally {
      clearInterval(ticker);
      setRunning(false);
      setRunningIds(new Set()); // clear any stragglers
    }
  }

  async function handleRunSingle(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    setRunningIds(prev => new Set(prev).add(id));
    try {
      const res = await fetch(`/api/v1/checks/${id}/run`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        toast.error(body?.detail ?? "Check run failed.");
      }
      // Always re-fetch the check after run to reflect any verdict change.
      const refreshed = await fetch("/api/v1/checks").then(r => r.ok ? r.json() : null);
      if (refreshed) {
        setChecks((refreshed as Parameters<typeof apiToRow>[0][]).map(apiToRow));
      }
    } finally {
      setRunningIds(prev => { const next = new Set(prev); next.delete(id); return next; });
    }
  }

  function handleRowCheckbox(e: React.MouseEvent, chk: CheckRow, idx: number) {
    e.stopPropagation();
    const next = new Set(selectedIds);
    if (e.shiftKey && lastCheckedIdxRef.current >= 0) {
      const from = Math.min(lastCheckedIdxRef.current, idx);
      const to = Math.max(lastCheckedIdxRef.current, idx);
      const adding = !selectedIds.has(chk.id);
      visibleChecks.slice(from, to + 1).forEach(c => adding ? next.add(c.id) : next.delete(c.id));
    } else {
      if (next.has(chk.id)) next.delete(chk.id);
      else next.add(chk.id);
      lastCheckedIdxRef.current = idx;
    }
    setSelectedIds(next);
  }

  async function handleBatchEnable(enabled: boolean) {
    const ids = Array.from(selectedIds);
    await fetch("/api/v1/checks/batch", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids, enabled }),
    }).catch(() => null);
    setChecks(prev => prev.map(c => selectedIds.has(c.id) ? { ...c, enabled } : c));
    setSelectedIds(new Set());
  }

  async function handleDeleteCheck(id: string) {
    const res = await fetch(`/api/v1/checks/${id}`, { method: "DELETE" }).catch(() => null);
    if (res?.ok) {
      setChecks(prev => prev.filter(c => c.id !== id));
      if (selectedId === id) setSelectedId(null);
      selectedIds.delete(id);
      setSelectedIds(new Set(selectedIds));
    } else {
      toast.error("Failed to delete check.");
    }
    setDeleteSingleConfirmId(null);
  }

  async function handleDeleteSelected() {
    const ids = Array.from(selectedIds);
    const res = await fetch("/api/v1/checks/batch-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    }).catch(() => null);
    if (res?.ok) {
      setChecks(prev => prev.filter(c => !selectedIds.has(c.id)));
      if (selectedId && selectedIds.has(selectedId)) setSelectedId(null);
      setSelectedIds(new Set());
    } else {
      toast.error("Failed to delete checks.");
    }
    setDeleteSelectedConfirm(false);
  }

  async function handleDeleteAll() {
    const res = await fetch("/api/v1/checks", { method: "DELETE" }).catch(() => null);
    if (res?.ok) {
      setChecks([]);
      setSelectedId(null);
      setSelectedIds(new Set());
    } else {
      toast.error("Failed to delete all checks.");
    }
    setDeleteAllConfirm(false);
  }

  function updateFilter(key: FilterKey, s: Set<string>) {
    setFilterSets(prev => ({ ...prev, [key]: s }));
  }

  // Build filter options from the full unfiltered dataset
  const filterOptions = useMemo((): Record<FilterKey, FilterOption[]> => {
    const count = (arr: string[]) => arr.reduce<Record<string, number>>((acc, v) => { acc[v] = (acc[v] ?? 0) + 1; return acc; }, {});

    const dcCounts = count(checks.map(c => `${c.dataset}.${c.column}`));
    const catCounts = count(checks.map(c => c.group));
    const chkCounts = count(checks.map(c => c.check));
    const vrdCounts = count(checks.map(c => c.verdict));

    return {
      dataset_col: Object.entries(dcCounts).sort(([a], [b]) => a.localeCompare(b)).map(([v, n]) => ({ value: v, label: v, count: n })),
      category: Object.entries(catCounts).sort(([a], [b]) => a.localeCompare(b)).map(([v, n]) => ({ value: v, label: CATEGORY_LABEL[v] ?? v, count: n })),
      check: Object.entries(chkCounts).sort(([a], [b]) => a.localeCompare(b)).map(([v, n]) => ({ value: v, label: v, count: n })),
      verdict: Object.entries(vrdCounts)
        .sort(([a], [b]) => {
          const ia = VERDICT_ORDER.indexOf(a);
          const ib = VERDICT_ORDER.indexOf(b);
          return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
        })
        .map(([v, n]) => ({ value: v, label: v.charAt(0).toUpperCase() + v.slice(1), count: n, color: VERDICT_COLOR[v] })),
    };
  }, [checks]);

  const visibleChecks = useMemo(() => checks.filter(c => {
    if (filterSets.dataset_col.size > 0 && !filterSets.dataset_col.has(`${c.dataset}.${c.column}`)) return false;
    if (filterSets.category.size > 0 && !filterSets.category.has(c.group)) return false;
    if (filterSets.check.size > 0 && !filterSets.check.has(c.check)) return false;
    if (filterSets.verdict.size > 0 && !filterSets.verdict.has(c.verdict)) return false;
    return true;
  }), [checks, filterSets]);

  const editingCheck = editingCheckId ? checks.find(c => c.id === editingCheckId) ?? null : null;
  const nextSchedule = schedules.filter(s => s.enabled && s.next_run_at).sort((a, b) => new Date(a.next_run_at!).getTime() - new Date(b.next_run_at!).getTime())[0] ?? null;
  const hasActiveFilters = Object.values(filterSets).some(s => s.size > 0);

  function clearAllFilters() {
    setFilterSets({ dataset_col: EMPTY_SET, category: EMPTY_SET, check: EMPTY_SET, verdict: EMPTY_SET });
  }

  function handleDownloadAll() {
    const yaml = visibleChecks.map(c => checkToYaml(c)).join("\n---\n");
    downloadYaml("checks.yaml", yaml);
  }

  async function handleImported() {
    const res = await fetch("/api/v1/checks").catch(() => null);
    if (res?.ok) {
      const data = await res.json() as Parameters<typeof apiToRow>[0][];
      setChecks(data.map(apiToRow));
    }
  }

  async function handleDownloadCheckSql(chk: CheckRow) {
    const res = await fetch(`/api/v1/checks/${chk.id}/sql`).catch(() => null);
    if (!res?.ok) {
      const body = await res?.json().catch(() => null);
      toast.error(body?.detail ?? "SQL not available for this check type.");
      return;
    }
    const { sql } = await res.json() as { sql: string };
    if (!sql) return;
    const blob = new Blob([sql], { type: "text/sql" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${chk.check}-${chk.column}.sql`;
    a.click();
    URL.revokeObjectURL(url);
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

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 44px)", overflow: "hidden" }}>
      {editingCheck && (
        <CheckEditModal check={editingCheck} onClose={() => setEditingCheckId(null)} onSave={updated => setChecks(prev => prev.map(c => c.id === updated.id ? updated : c))} />
      )}
      {scheduleOpen && (
        <ScheduleModal schedules={schedules} onClose={() => setScheduleOpen(false)} onCreated={s => setSchedules(prev => [...prev, s])} onDeleted={id => setSchedules(prev => prev.filter(s => s.id !== id))} onToggled={updated => setSchedules(prev => prev.map(s => s.id === updated.id ? updated : s))} />
      )}
      {importOpen && (
        <ImportYamlModal onClose={() => setImportOpen(false)} onImported={handleImported} />
      )}

      {/* Top action bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-line shrink-0" style={{ background: "var(--bg-1)" }}>
        <div className="flex items-center gap-4">
          <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Checks</span>
          {lastRunAt && <span className="t-micro" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>Last run: {fmtTime(lastRunAt)}</span>}
          {nextSchedule && <span className="t-micro" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>· Next: {fmtNextRun(nextSchedule.next_run_at)}</span>}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setImportOpen(true)} className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80" style={{ background: "var(--bg-2)", color: "var(--fg-0)", borderColor: "var(--line)" }}>
            <Upload size={12} strokeWidth={1.6} /> Import YAML
          </button>
          {deleteAllConfirm ? (
            <div className="flex items-center gap-1.5">
              <span className="t-small" style={{ color: "var(--fail)" }}>Delete all checks?</span>
              <button onClick={handleDeleteAll} className="px-3 py-1.5 t-small border transition-colors hover:opacity-80" style={{ background: "var(--fail)", color: "#fff", borderColor: "var(--fail)" }}>Yes, delete all</button>
              <button onClick={() => setDeleteAllConfirm(false)} className="px-3 py-1.5 t-small border transition-colors hover:opacity-80" style={{ background: "var(--bg-2)", color: "var(--fg-1)", borderColor: "var(--line)" }}>Cancel</button>
            </div>
          ) : (
            <button onClick={() => setDeleteAllConfirm(true)} disabled={checks.length === 0} className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40" style={{ background: "var(--bg-2)", color: "var(--fg-1)", borderColor: "var(--line)" }}>
              <Trash2 size={12} strokeWidth={1.6} /> Delete All
            </button>
          )}
          <button onClick={handleDownloadAll} disabled={visibleChecks.length === 0} className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40" style={{ background: "var(--bg-2)", color: "var(--fg-0)", borderColor: "var(--line)" }}>
            <Download size={12} strokeWidth={1.6} /> Export YAML
          </button>
          <button onClick={handleRunNow} disabled={running} className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40" style={{ background: runDone ? "var(--pass)" : "var(--bg-2)", color: runDone ? "var(--bg-0)" : "var(--fg-0)", borderColor: runDone ? "var(--pass)" : "var(--line)" }}>
            {running
              ? <Loader2 size={12} strokeWidth={1.6} className="animate-spin" />
              : runDone
                ? null
                : <Play size={12} strokeWidth={1.6} />}
            {running
              ? `Running... ${runningElapsed}s`
              : runDone
                ? "Done"
                : "Run Now"}
          </button>
          <button onClick={() => setScheduleOpen(true)} className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80" style={{ background: schedules.some(s => s.enabled) ? "var(--accent-bg)" : "var(--bg-2)", color: schedules.some(s => s.enabled) ? "var(--accent)" : "var(--fg-1)", borderColor: schedules.some(s => s.enabled) ? "var(--accent)" : "var(--line)" }}>
            <CalendarClock size={12} strokeWidth={1.6} />
            {schedules.some(s => s.enabled) ? `Scheduled (${schedules.filter(s => s.enabled).length})` : "Schedule"}
          </button>
        </div>
      </div>

      {/* 2-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex flex-col flex-1 border-r border-line overflow-hidden">
          {/* Count + batch actions bar */}
          <div className="px-3 py-1.5 border-b border-line t-micro flex items-center gap-3" style={{ background: selectedIds.size > 0 ? "var(--accent-bg)" : "var(--bg-1)", flexShrink: 0, color: "var(--fg-3)" }}>
            {selectedIds.size > 0 ? (
              <>
                <span style={{ color: "var(--accent)" }}>{selectedIds.size} selected</span>
                <button onClick={() => handleBatchEnable(true)} className="px-2 py-0.5 border border-line hover:border-accent transition-colors" style={{ color: "var(--fg-1)" }}>Enable</button>
                <button onClick={() => handleBatchEnable(false)} className="px-2 py-0.5 border border-line hover:border-accent transition-colors" style={{ color: "var(--fg-1)" }}>Disable</button>
                {deleteSelectedConfirm ? (
                  <>
                    <span style={{ color: "var(--fail)" }}>Delete {selectedIds.size} check{selectedIds.size !== 1 ? "s" : ""}?</span>
                    <button onClick={handleDeleteSelected} className="px-2 py-0.5 border transition-colors" style={{ color: "var(--fail)", borderColor: "var(--fail)" }}>Yes</button>
                    <button onClick={() => setDeleteSelectedConfirm(false)} className="px-2 py-0.5 border border-line transition-colors" style={{ color: "var(--fg-2)" }}>No</button>
                  </>
                ) : (
                  <button onClick={() => setDeleteSelectedConfirm(true)} className="flex items-center gap-1 px-2 py-0.5 border border-line hover:border-fail transition-colors" style={{ color: "var(--fg-2)" }}>
                    <Trash2 size={9} strokeWidth={2} /> Delete
                  </button>
                )}
                <button onClick={() => setSelectedIds(new Set())} className="flex items-center gap-1 hover:underline" style={{ color: "var(--fg-2)" }}>
                  <X size={9} strokeWidth={2} /> Deselect all
                </button>
              </>
            ) : (
              <>
                <span className="font-mono">
                  {visibleChecks.length} check{visibleChecks.length !== 1 ? "s" : ""}
                  {visibleChecks.length !== checks.length && ` of ${checks.length}`}
                </span>
                {hasActiveFilters && (
                  <button onClick={clearAllFilters} className="flex items-center gap-1 hover:underline" style={{ color: "var(--accent)" }}>
                    <X size={9} strokeWidth={2} /> Clear filters
                  </button>
                )}
              </>
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="px-4 py-8 t-small text-center" style={{ color: "var(--fg-3)" }}>Loading checks...</div>
            ) : checks.length === 0 ? (
              <div className="px-4 py-8 t-small text-center" style={{ color: "var(--fg-2)" }}>No checks yet. Add a source to get started.</div>
            ) : (
              <table className="w-full" style={{ borderCollapse: "collapse" }}>
                <thead style={{ position: "sticky", top: 0, zIndex: 10, background: "var(--bg-1)" }}>
                  <tr className="border-b border-line">
                    {/* Select-all checkbox */}
                    <th className="px-3 py-2 w-8">
                      <input
                        type="checkbox"
                        checked={visibleChecks.length > 0 && visibleChecks.every(c => selectedIds.has(c.id))}
                        ref={el => { if (el) el.indeterminate = selectedIds.size > 0 && !visibleChecks.every(c => selectedIds.has(c.id)); }}
                        onChange={e => setSelectedIds(e.target.checked ? new Set(visibleChecks.map(c => c.id)) : new Set())}
                        style={{ accentColor: "var(--accent)", width: 13, height: 13 }}
                      />
                    </th>
                    <FilterHeader label="Dataset.Column" {...filterHeaderProps("dataset_col")} />
                    <FilterHeader label="Category" {...filterHeaderProps("category")} />
                    <FilterHeader label="Check" {...filterHeaderProps("check")} />
                    <FilterHeader label="Verdict" {...filterHeaderProps("verdict")} />
                    <th className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>Result</th>
                    <th className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>Score</th>
                    <th className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>Last run</th>
                    <th className="px-3 py-2 w-20" />
                  </tr>
                </thead>
                <tbody>
                  {visibleChecks.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-8 t-small text-center" style={{ color: "var(--fg-2)" }}>No checks match the current filters.</td>
                    </tr>
                  ) : visibleChecks.map((chk, idx) => {
                    const isSelected = selectedId === chk.id;
                    const isChecked = selectedIds.has(chk.id);
                    return (
                      <tr
                        key={chk.id}
                        onClick={() => setSelectedId(isSelected ? null : chk.id)}
                        className="border-b border-line last:border-0 cursor-pointer transition-colors align-middle"
                        style={{ background: isSelected ? "var(--bg-2)" : undefined, opacity: chk.enabled ? 1 : 0.45 }}
                        onMouseEnter={e => { if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = "var(--bg-2)"; }}
                        onMouseLeave={e => { if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = ""; }}
                      >
                        <td className="px-3 py-2 w-8 align-middle" onClick={e => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}}
                            onClick={e => handleRowCheckbox(e as React.MouseEvent, chk, idx)}
                            style={{ accentColor: "var(--accent)", width: 13, height: 13, display: "block" }}
                          />
                        </td>
                        <td className="px-3 py-2 align-middle"><span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{chk.dataset}.{chk.column}</span></td>
                        <td className="px-3 py-2 t-small" style={{ color: "var(--fg-2)" }}>{CATEGORY_LABEL[chk.group] ?? chk.group}</td>
                        <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>{chk.check}</td>
                        <td className="px-3 py-2">
                          <span className="t-small" style={{ color: VERDICT_COLOR[chk.verdict] ?? "var(--fg-3)" }}>
                            {chk.verdict.charAt(0).toUpperCase() + chk.verdict.slice(1)}
                          </span>
                        </td>
                        <td className="px-3 py-2 t-small font-mono" style={{ color: chk.verdict === "pending" || chk.score === null ? "var(--fg-3)" : "var(--fg-1)" }}>
                          {chk.verdict === "pending" || chk.score === null
                            ? "--"
                            : <span title={String(chk.score)}>{fmtScore(chk.score)}</span>}
                        </td>
                        <td className="px-3 py-2 t-small font-mono">
                          {(() => {
                            const dqt = computeDqtScore(chk);
                            if (dqt === null) return <span style={{ color: "var(--fg-3)" }}>--</span>;
                            const color = dqt === 100 ? "var(--pass)" : dqt === 0 ? "var(--fail)" : "var(--warn)";
                            return <span style={{ color }}>{dqt}%</span>;
                          })()}
                        </td>
                        <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-3)", whiteSpace: "nowrap" }}>
                          {chk.ran_at
                            ? <span title={new Date(chk.ran_at).toLocaleString()}>{fmtTime(chk.ran_at)}</span>
                            : <span>--</span>}
                        </td>
                        <td className="px-3 py-2 w-24 text-right" onClick={e => e.stopPropagation()}>
                          {deleteSingleConfirmId === chk.id ? (
                            <div className="flex items-center justify-end gap-1">
                              <span className="t-micro" style={{ color: "var(--fail)" }}>Delete?</span>
                              <button onClick={() => handleDeleteCheck(chk.id)} className="t-micro px-1.5 py-0.5 border transition-colors" style={{ color: "var(--fail)", borderColor: "var(--fail)" }}>Yes</button>
                              <button onClick={() => setDeleteSingleConfirmId(null)} className="t-micro px-1.5 py-0.5 border border-line transition-colors" style={{ color: "var(--fg-2)" }}>No</button>
                            </div>
                          ) : (
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={e => handleRunSingle(e, chk.id)}
                                disabled={runningIds.has(chk.id)}
                                className="flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors disabled:opacity-40"
                                style={{ color: "var(--fg-3)" }}
                                title="Run this check"
                              >
                                {runningIds.has(chk.id)
                                  ? <Loader2 size={11} strokeWidth={1.6} className="animate-spin" />
                                  : <Play size={11} strokeWidth={1.6} />}
                              </button>
                              <button onClick={() => setEditingCheckId(chk.id)} className="inline-flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors" style={{ color: "var(--fg-3)" }} title="Edit check"><Pencil size={11} strokeWidth={1.6} /></button>
                              <button onClick={() => setDeleteSingleConfirmId(chk.id)} className="flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors" style={{ color: "var(--fg-3)" }} title="Delete this check">
                                <Trash2 size={11} strokeWidth={1.6} />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right: detail / author */}
        <div className="overflow-y-auto flex-shrink-0 relative" style={{ width: rightWidth, background: "var(--bg-1)" }}>
          <div
            onMouseDown={onRightPanelResizeStart}
            style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 4, cursor: "col-resize", zIndex: 10, background: "transparent", transition: "background 120ms" }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(157,208,176,0.3)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          />
          <RightPanel selectedCheckId={selectedId} checks={checks} onEditCheck={setEditingCheckId} onRunSingle={handleRunSingle} runningIds={runningIds} onCheckAdded={chk => setChecks(prev => [chk, ...prev])} />
        </div>
      </div>
    </div>
  );
}

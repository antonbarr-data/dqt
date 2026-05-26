"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { ChevronDown, Download, ListFilter, Loader2, Pencil, Plus, Sparkles, Trash2, Upload, X, Check } from "lucide-react";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface MetricSummary {
  fqn: string;
  display_name: string;
  kind: string;
  dataset: string;
  source_id: string | null;
  column_name: string | null;
  tags: string[];
  current_verdict: string | null;
  pinned: boolean;
}

interface DatasetItem {
  id: string;
  source: string;
  schema: string;
  source_id?: string;
}

interface SuggestedMetric {
  name: string;
  definition: string;
  kind: string;
  grain: string | null;
  additivity: string | null;
  good_direction: string | null;
  cadence: string | null;
  dataset: string;
  display_name: string;
  source_column: string;
  confidence: number;
  reasoning: string;
}

type MetricFilterKey = "dataset" | "kind" | "verdict";
const EMPTY_SET = new Set<string>();

interface FilterOption {
  value: string;
  label: string;
  count: number;
  color?: string;
}

// ---------------------------------------------------------------------------
// Filter dropdown — portal-based, Excel-style multi-select with search
// ---------------------------------------------------------------------------

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

  const visibleOptions = options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()));
  const allChecked = visibleOptions.length > 0 && visibleOptions.every(o => selected.has(o.value));
  const someChecked = visibleOptions.some(o => selected.has(o.value));

  function toggleAll() {
    const next = new Set(selected);
    if (allChecked) visibleOptions.forEach(o => next.delete(o.value));
    else visibleOptions.forEach(o => next.add(o.value));
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
        position: "fixed", top: pos.top, left: pos.left, zIndex: 1000,
        width: 240, background: "var(--bg-1)",
        border: "1px solid var(--line)", boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
      }}
    >
      <div className="p-2 border-b border-line">
        <input autoFocus type="text" placeholder="Search..." value={search}
          onChange={e => setSearch(e.target.value)} style={baseInput} />
      </div>
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-line" style={{ background: "var(--bg-0)" }}>
        <label className="flex items-center gap-2 cursor-pointer t-micro" style={{ color: "var(--fg-1)" }}>
          <input type="checkbox" checked={allChecked}
            ref={el => { if (el) el.indeterminate = someChecked && !allChecked; }}
            onChange={toggleAll}
            style={{ accentColor: "var(--accent)", width: 12, height: 12 }} />
          Select all ({visibleOptions.length})
        </label>
        {selected.size > 0 && (
          <button onClick={() => { onChange(new Set()); onClose(); }}
            className="t-micro hover:underline" style={{ color: "var(--accent)" }}>
            Clear
          </button>
        )}
      </div>
      <div style={{ maxHeight: 240, overflowY: "auto" }}>
        {visibleOptions.length === 0 ? (
          <p className="px-3 py-2 t-micro" style={{ color: "var(--fg-3)" }}>No matches</p>
        ) : visibleOptions.map(o => (
          <label key={o.value}
            className="flex items-center gap-2 px-2 py-1.5 cursor-pointer transition-colors"
            style={{ color: "var(--fg-0)" }}
            onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-2)")}
            onMouseLeave={e => (e.currentTarget.style.background = "")}
          >
            <input type="checkbox" checked={selected.has(o.value)}
              onChange={() => toggle(o.value)}
              style={{ accentColor: "var(--accent)", width: 12, height: 12, flexShrink: 0 }} />
            {o.color && <span style={{ width: 6, height: 6, background: o.color, flexShrink: 0, display: "inline-block" }} />}
            <span className="t-small truncate flex-1">{o.label}</span>
            <span className="t-micro font-mono flex-shrink-0" style={{ color: "var(--fg-3)" }}>{o.count}</span>
          </label>
        ))}
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
  filterKey: MetricFilterKey;
  options: FilterOption[];
  selected: Set<string>;
  openFilter: MetricFilterKey | null;
  onOpen: (key: MetricFilterKey) => void;
  onClose: () => void;
  onChange: (key: MetricFilterKey, s: Set<string>) => void;
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
          background: "transparent", border: "none", padding: 0, cursor: "pointer",
          letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "inherit",
          fontFamily: "inherit", fontWeight: "inherit",
        }}
      >
        {label}
        <ListFilter size={10} strokeWidth={1.6} style={{ opacity: isActive || isOpen ? 1 : 0.4 }} />
        {isActive && (
          <span className="font-mono"
            style={{ fontSize: 9, background: "var(--accent)", color: "var(--bg-0)", padding: "0 3px", lineHeight: "14px", display: "inline-block" }}>
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


const METRIC_KINDS = ["ratio", "count", "sum", "model"] as const;
const KIND_HINT: Record<string, string> = {
  ratio: "fraction, rate, or average",
  count: "row or event count",
  sum: "summed total",
  model: "ML model output",
};

const VERDICT_COLOR: Record<string, string> = {
  pass: "var(--pass)", warn: "var(--warn)", fail: "var(--fail)", pending: "var(--fg-3)",
};

function metricToYaml(m: MetricSummary): string {
  const lines = [
    `display_name: ${m.display_name}`,
    `kind: ${m.kind}`,
    `dataset: ${m.dataset}`,
  ];
  if (m.tags?.length > 0) lines.push(`tags: [${m.tags.join(", ")}]`);
  return lines.join("\n");
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

function parseMetricYamlBlock(block: string): Record<string, string> | null {
  const result: Record<string, string> = {};
  for (const line of block.split("\n")) {
    const colonIdx = line.indexOf(": ");
    if (colonIdx < 0) continue;
    const key = line.slice(0, colonIdx).trim();
    const val = line.slice(colonIdx + 2).trim();
    if (key && val) result[key] = val;
  }
  return result.display_name && result.dataset ? result : null;
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [confirmDeleteFqn, setConfirmDeleteFqn] = useState<string | null>(null);
  const [deletingFqn, setDeletingFqn] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formKind, setFormKind] = useState<"ratio" | "count" | "sum" | "model">("ratio");
  const [formDataset, setFormDataset] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Column filters
  const [filterSets, setFilterSets] = useState<Record<MetricFilterKey, Set<string>>>({
    dataset: EMPTY_SET, kind: EMPTY_SET, verdict: EMPTY_SET,
  });
  const [openFilter, setOpenFilter] = useState<MetricFilterKey | null>(null);
  const headerEls = useRef<Partial<Record<MetricFilterKey, HTMLTableCellElement | null>>>({});

  // Selection state
  const [selectedFqns, setSelectedFqns] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);
  const selectAllRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Inline row edit state
  const [editingRowFqn, setEditingRowFqn] = useState<string | null>(null);
  const [editRow, setEditRow] = useState<{ display_name: string; kind: string; dataset: string } | null>(null);
  const [savingRow, setSavingRow] = useState(false);

  // Suggest state
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [selectedDatasets, setSelectedDatasets] = useState<string[]>([]);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestedMetric[]>([]);
  const [addedFqns, setAddedFqns] = useState<Set<string>>(new Set());
  const [addingName, setAddingName] = useState<string | null>(null);
  const [suggestError, setSuggestError] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/metrics`);
      if (res.ok) setMetrics(await res.json());
      else setFetchError("Failed to load metrics.");
    } catch {
      setFetchError("Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadMetrics(); }, [loadMetrics]);

  // Build filter options from unfiltered data
  const filterOptions = useMemo((): Record<MetricFilterKey, FilterOption[]> => {
    const count = (arr: string[]) =>
      arr.reduce<Record<string, number>>((acc, v) => { acc[v] = (acc[v] ?? 0) + 1; return acc; }, {});

    const datasetCounts = count(metrics.map(m => m.dataset).filter(Boolean));
    const kindCounts = count(metrics.map(m => m.kind));
    const verdictCounts = count(metrics.map(m => m.current_verdict ?? "pending"));

    return {
      dataset: Object.entries(datasetCounts).sort(([a], [b]) => a.localeCompare(b))
        .map(([v, n]) => ({ value: v, label: v, count: n })),
      kind: Object.entries(kindCounts).sort(([a], [b]) => a.localeCompare(b))
        .map(([v, n]) => ({ value: v, label: v, count: n })),
      verdict: Object.entries(verdictCounts)
        .map(([v, n]) => ({ value: v, label: v.charAt(0).toUpperCase() + v.slice(1), count: n, color: VERDICT_COLOR[v] })),
    };
  }, [metrics]);

  const filtered = useMemo(() => metrics.filter(m => {
    if (filterSets.dataset.size > 0 && !filterSets.dataset.has(m.dataset)) return false;
    if (filterSets.kind.size > 0 && !filterSets.kind.has(m.kind)) return false;
    if (filterSets.verdict.size > 0 && !filterSets.verdict.has(m.current_verdict ?? "pending")) return false;
    return true;
  }), [metrics, filterSets]);

  const hasActiveFilters = Object.values(filterSets).some(s => s.size > 0);

  function updateFilter(key: MetricFilterKey, s: Set<string>) {
    setFilterSets(prev => ({ ...prev, [key]: s }));
  }

  function clearAllFilters() {
    setFilterSets({ dataset: EMPTY_SET, kind: EMPTY_SET, verdict: EMPTY_SET });
  }

  const filterHeaderProps = (key: MetricFilterKey) => ({
    filterKey: key,
    options: filterOptions[key],
    selected: filterSets[key],
    openFilter,
    onOpen: (k: MetricFilterKey) => setOpenFilter(k),
    onClose: () => setOpenFilter(null),
    onChange: updateFilter,
    headerRef: (el: HTMLTableCellElement | null) => { headerEls.current[key] = el; },
  });

  // Sync select-all indeterminate state
  useEffect(() => {
    if (!selectAllRef.current) return;
    selectAllRef.current.indeterminate = selectedFqns.size > 0 && selectedFqns.size < filtered.length;
  }, [selectedFqns, filtered]);

  function toggleSelect(fqn: string) {
    setSelectedFqns((prev) => {
      const next = new Set(prev);
      if (next.has(fqn)) next.delete(fqn);
      else next.add(fqn);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedFqns.size === filtered.length) {
      setSelectedFqns(new Set());
    } else {
      setSelectedFqns(new Set(filtered.map((m) => m.fqn)));
    }
  }

  function handleExportYaml() {
    const toExport = selectedFqns.size > 0
      ? filtered.filter((m) => selectedFqns.has(m.fqn))
      : filtered;
    const content = toExport.map(metricToYaml).join("\n---\n");
    downloadYaml("metrics.yaml", content);
  }

  async function handleImportYaml(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const text = await file.text();
      const blocks = text.split(/^---$/m).filter((b) => b.trim());
      const parsed = blocks.map(parseMetricYamlBlock).filter(Boolean) as Record<string, string>[];
      if (parsed.length === 0) { toast.error("No valid metrics found in file"); return; }
      const res = await fetch(`${API}/api/v1/metrics/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metrics: parsed.map((p) => ({
            display_name: p.display_name,
            kind: p.kind ?? "ratio",
            dataset: p.dataset,
            description: p.description ?? "",
          })),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const count = Array.isArray(data) ? data.length : (data.created ?? parsed.length);
        toast.success(`Imported ${count} metric${count !== 1 ? "s" : ""}`);
        await loadMetrics();
      } else {
        toast.error("Import failed");
      }
    } catch {
      toast.error("Failed to read file");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleBulkDelete() {
    if (selectedFqns.size === 0) return;
    const count = selectedFqns.size;
    setBulkDeleting(true);
    try {
      await Promise.all(
        Array.from(selectedFqns).map((fqn) =>
          fetch(`${API}/api/v1/metrics/${encodeURIComponent(fqn)}`, { method: "DELETE" })
        )
      );
      setMetrics((prev) => prev.filter((m) => !selectedFqns.has(m.fqn)));
      setSelectedFqns(new Set());
      setConfirmBulkDelete(false);
      toast.success(`Deleted ${count} metric${count !== 1 ? "s" : ""}`);
    } finally {
      setBulkDeleting(false);
    }
  }

  function startEditRow(m: MetricSummary) {
    setEditingRowFqn(m.fqn);
    setEditRow({ display_name: m.display_name, kind: m.kind, dataset: m.dataset });
  }

  function cancelEditRow() {
    setEditingRowFqn(null);
    setEditRow(null);
  }

  async function saveEditRow(fqn: string) {
    if (!editRow) return;
    setSavingRow(true);
    try {
      const res = await fetch(`${API}/api/v1/metrics/${encodeURIComponent(fqn)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: editRow.display_name,
          kind: editRow.kind,
          dataset: editRow.dataset,
        }),
      });
      if (res.ok) {
        setMetrics((prev) => prev.map((m) => m.fqn === fqn ? { ...m, ...editRow } : m));
        cancelEditRow();
      } else {
        toast.error("Failed to save");
      }
    } finally {
      setSavingRow(false);
    }
  }

  async function openSuggest() {
    setSuggestOpen(true);
    setSuggestions([]);
    setSuggestError(null);
    if (datasets.length === 0) {
      const res = await fetch(`${API}/api/v1/datasets`).catch(() => null);
      if (res?.ok) {
        const data: DatasetItem[] = await res.json();
        setDatasets(data);
      }
    }
  }

  function toggleDataset(id: string) {
    setSelectedDatasets((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  }

  async function runSuggest() {
    if (selectedDatasets.length === 0) return;
    setSuggesting(true);
    setSuggestError(null);
    setSuggestions([]);
    try {
      const results = await Promise.all(
        selectedDatasets.map(async (datasetId) => {
          const res = await fetch(`${API}/api/v1/datasets/${encodeURIComponent(datasetId)}/columns`);
          if (!res.ok) throw new Error(`Could not fetch columns for ${datasetId}`);
          const cols: { name: string; data_type: string; nullable: boolean }[] = await res.json();
          return cols.map((c) => ({ dataset: datasetId, column: c.name, data_type: c.data_type, null_rate: 0.0 }));
        })
      );
      const allCols = results.flat();
      if (allCols.length === 0) throw new Error("No columns found in the selected datasets");

      const sugRes = await fetch(`${API}/api/v1/metrics/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ columns: allCols }),
      });
      if (!sugRes.ok) throw new Error("Suggestion failed");
      const result = await sugRes.json();
      if (!result.metrics || result.metrics.length === 0) {
        setSuggestError("No metric candidates found in the selected datasets. Try fact or aggregation tables.");
      } else {
        setSuggestions(result.metrics);
      }
    } catch (e: unknown) {
      setSuggestError(e instanceof Error ? e.message : "Failed to generate suggestions");
    } finally {
      setSuggesting(false);
    }
  }

  async function addSuggestion(s: SuggestedMetric) {
    setAddingName(s.name);
    try {
      const res = await fetch(`${API}/api/v1/metrics/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metrics: [{
            display_name: s.display_name || s.name,
            kind: s.kind || "ratio",
            dataset: s.dataset,
            description: s.definition || "",
            grain: s.grain || null,
            additivity: s.additivity || null,
            good_direction: s.good_direction || null,
            refresh_cadence: s.cadence || null,
          }],
        }),
      });
      if (res.ok) {
        setAddedFqns((prev) => new Set(Array.from(prev).concat(s.name)));
        await loadMetrics();
      }
    } finally {
      setAddingName(null);
    }
  }

  function handleDeleteMetric(fqn: string) {
    setDeletingFqn(true);
    fetch(`${API}/api/v1/metrics/${encodeURIComponent(fqn)}`, { method: "DELETE" })
      .then(() => setMetrics((prev) => prev.filter((m) => m.fqn !== fqn)))
      .catch(() => {})
      .finally(() => { setDeletingFqn(false); setConfirmDeleteFqn(null); });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formName.trim() || !formDataset.trim()) { setFormError("Name and dataset are required."); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      const res = await fetch(`${API}/api/v1/metrics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: formName.trim(),
          kind: formKind,
          dataset: formDataset.trim(),
          description: formDescription.trim(),
        }),
      });
      if (res.status === 201) {
        setFormName(""); setFormKind("ratio"); setFormDataset(""); setFormDescription("");
        setFormOpen(false);
        await loadMetrics();
      } else if (res.status === 409) {
        setFormError("A metric with this name already exists for that dataset.");
      } else {
        const err = await res.json().catch(() => ({}));
        setFormError(err.detail || "Failed to create metric.");
      }
    } catch { setFormError("Network error."); }
    finally { setSubmitting(false); }
  }

  const checkboxStyle: React.CSSProperties = {
    width: 13, height: 13, flexShrink: 0, cursor: "pointer", accentColor: "var(--accent)",
  };

  return (
    <div className="p-6 overflow-auto">
      {/* Hidden file input for YAML import */}
      <input ref={fileInputRef} type="file" accept=".yaml,.yml" className="hidden" onChange={handleImportYaml} />

      <div className="flex items-baseline justify-between mb-6">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Metrics</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportYaml}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:opacity-80"
            style={{ color: "var(--fg-1)", background: "var(--bg-2)" }}
            title={selectedFqns.size > 0 ? `Export ${selectedFqns.size} selected` : "Export all metrics"}
          >
            <Download size={12} strokeWidth={1.8} />
            Export YAML
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:opacity-80 disabled:opacity-40"
            style={{ color: "var(--fg-1)", background: "var(--bg-2)" }}
          >
            {importing ? <Loader2 size={12} strokeWidth={2} className="animate-spin" /> : <Upload size={12} strokeWidth={1.8} />}
            Import YAML
          </button>
          <button
            onClick={() => suggestOpen ? setSuggestOpen(false) : openSuggest()}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80"
            style={{
              background: suggestOpen ? "rgba(99,102,241,0.1)" : "var(--bg-2)",
              color: suggestOpen ? "var(--accent)" : "var(--fg-1)",
              borderColor: suggestOpen ? "var(--accent)" : "var(--line)",
            }}
          >
            <Sparkles size={12} strokeWidth={1.8} />
            Suggest metrics
          </button>
          <button
            onClick={() => { setFormOpen((v) => !v); setFormError(null); }}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80"
            style={{
              background: formOpen ? "var(--accent-bg)" : "var(--bg-2)",
              color: formOpen ? "var(--accent)" : "var(--fg-0)",
              borderColor: formOpen ? "var(--accent)" : "var(--line)",
            }}
          >
            <Plus size={11} strokeWidth={1.6} />
            New metric
          </button>
        </div>
      </div>

      {/* Bulk action toolbar */}
      {selectedFqns.size > 0 && (
        <div className="flex items-center gap-3 px-3 py-2 mb-4 border border-line"
             style={{ background: "var(--bg-1)" }}>
          <span className="t-small" style={{ color: "var(--fg-1)" }}>
            <span style={{ color: "var(--accent)", fontWeight: 500 }}>{selectedFqns.size}</span> selected
          </span>
          <button
            onClick={handleExportYaml}
            className="flex items-center gap-1 px-2 py-1 t-micro border border-line hover:opacity-80"
            style={{ color: "var(--fg-2)" }}
          >
            <Download size={10} strokeWidth={1.8} />
            Export
          </button>
          {!confirmBulkDelete ? (
            <button
              onClick={() => setConfirmBulkDelete(true)}
              className="flex items-center gap-1 px-2 py-1 t-micro border hover:opacity-80"
              style={{ borderColor: "var(--fail)", color: "var(--fail)" }}
            >
              <Trash2 size={10} strokeWidth={1.8} />
              Delete {selectedFqns.size}
            </button>
          ) : (
            <div className="flex items-center gap-1.5">
              <span className="t-micro" style={{ color: "var(--fail)" }}>Delete {selectedFqns.size} metrics?</span>
              <button
                onClick={handleBulkDelete}
                disabled={bulkDeleting}
                className="flex items-center gap-1 px-2 py-0.5 t-micro border transition-colors disabled:opacity-40"
                style={{ borderColor: "var(--fail)", color: "var(--fail)", background: "rgba(224,123,110,0.08)" }}
              >
                {bulkDeleting ? <Loader2 size={10} strokeWidth={2} className="animate-spin" /> : "Confirm"}
              </button>
              <button onClick={() => setConfirmBulkDelete(false)} className="t-micro px-1 hover:opacity-60" style={{ color: "var(--fg-3)" }}>✕</button>
            </div>
          )}
          <button
            onClick={() => { setSelectedFqns(new Set()); setConfirmBulkDelete(false); }}
            className="ml-auto t-micro hover:opacity-60"
            style={{ color: "var(--fg-3)" }}
          >
            Clear selection
          </button>
        </div>
      )}

      {/* Suggest panel */}
      {suggestOpen && (
        <div className="mb-6 border border-line" style={{ background: "var(--bg-1)" }}>
          <div className="px-4 py-3 border-b border-line flex items-center justify-between">
            <span className="t-small" style={{ color: "var(--fg-0)" }}>Suggest metrics from a dataset</span>
            <button onClick={() => setSuggestOpen(false)} className="hover:opacity-70">
              <X size={14} style={{ color: "var(--fg-3)" }} />
            </button>
          </div>
          <div className="p-4">
            {datasets.length === 0 && !suggesting && (
              <p className="t-small" style={{ color: "var(--fg-3)" }}>No datasets found. Connect a source first.</p>
            )}
            {datasets.length > 0 && suggestions.length === 0 && !suggesting && (
              <div>
                <label className="t-micro block mb-2" style={{ color: "var(--fg-2)" }}>
                  Select datasets
                  {selectedDatasets.length > 0 && (
                    <span className="ml-2 font-mono" style={{ color: "var(--accent)" }}>{selectedDatasets.length} selected</span>
                  )}
                </label>
                <div className="border border-line mb-3" style={{ maxHeight: 200, overflowY: "auto" }}>
                  {datasets.map((d) => {
                    const checked = selectedDatasets.includes(d.id);
                    return (
                      <label key={d.id}
                        className="flex items-center gap-2.5 px-3 py-2 cursor-pointer hover:bg-bg-2 border-b border-line last:border-0"
                        style={{ color: checked ? "var(--fg-0)" : "var(--fg-2)" }}
                      >
                        <input type="checkbox" checked={checked} onChange={() => toggleDataset(d.id)}
                          className="accent-accent" style={{ width: 13, height: 13, flexShrink: 0 }} />
                        <span className="t-small font-mono">{d.id}</span>
                      </label>
                    );
                  })}
                </div>
                <button onClick={runSuggest} disabled={selectedDatasets.length === 0}
                  className="flex items-center gap-1.5 px-4 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
                  style={{ color: "var(--accent)", borderColor: "var(--accent)" }}>
                  <Sparkles size={12} strokeWidth={1.8} />
                  Analyze {selectedDatasets.length > 1 ? `${selectedDatasets.length} datasets` : ""}
                </button>
              </div>
            )}
            {suggesting && (
              <div className="flex items-center gap-2 py-4">
                <Loader2 size={14} strokeWidth={2} className="animate-spin" style={{ color: "var(--accent)" }} />
                <span className="t-small" style={{ color: "var(--fg-2)" }}>Analyzing columns and generating suggestions...</span>
              </div>
            )}
            {suggestError && <p className="t-small" style={{ color: "var(--fail)" }}>{suggestError}</p>}
            {suggestions.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="t-small" style={{ color: "var(--fg-2)" }}>
                    <span style={{ color: "var(--fg-0)" }}>{suggestions.length}</span> suggestions
                    {selectedDatasets.length === 1
                      ? <> for <span className="font-mono" style={{ color: "var(--fg-1)" }}>{selectedDatasets[0]}</span></>
                      : <> across <span style={{ color: "var(--fg-1)" }}>{selectedDatasets.length} datasets</span></>}
                  </p>
                  <button onClick={() => { setSuggestions([]); setSuggestError(null); }}
                    className="t-micro border border-line px-2 py-0.5 hover:opacity-80"
                    style={{ color: "var(--fg-3)" }}>
                    Change selection
                  </button>
                </div>
                <div className="divide-y divide-line border border-line">
                  {suggestions.map((s, i) => {
                    const added = addedFqns.has(s.name);
                    return (
                      <div key={i} className="px-4 py-3 flex items-start gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                            <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{s.display_name || s.name}</span>
                            {s.kind && <span className="t-micro px-1.5 py-0.5 border border-line font-mono" style={{ color: "var(--fg-2)" }}>{s.kind}</span>}
                            {s.additivity && <span className="t-micro px-1.5 py-0.5 border border-line" style={{ color: "var(--fg-3)" }}>{s.additivity}</span>}
                            {s.good_direction && (
                              <span className="t-micro px-1.5 py-0.5 border border-line"
                                style={{ color: s.good_direction === "up" ? "var(--pass)" : s.good_direction === "down" ? "var(--fail)" : "var(--warn)" }}>
                                {s.good_direction === "up" ? "↑ up" : s.good_direction === "down" ? "↓ down" : "⇔ in-band"}
                              </span>
                            )}
                          </div>
                          {s.definition && <p className="t-small" style={{ color: "var(--fg-2)" }}>{s.definition}</p>}
                          {s.reasoning && <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{s.reasoning}</p>}
                        </div>
                        <button onClick={() => addSuggestion(s)} disabled={added || addingName === s.name}
                          className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
                          style={{ color: added ? "var(--pass)" : "var(--accent)", borderColor: added ? "var(--pass)" : "var(--accent)" }}>
                          {addingName === s.name ? <Loader2 size={11} strokeWidth={2} className="animate-spin" />
                            : added ? "Added ✓"
                            : <><Plus size={11} strokeWidth={2} /> Add</>}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* New metric inline form */}
      {formOpen && (
        <form onSubmit={handleSubmit} className="mb-6 border border-line p-4 space-y-3" style={{ background: "var(--bg-1)" }}>
          <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>New metric</p>
          <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Name</label>
              <input type="text" value={formName} onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Conversion rate"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }} />
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Dataset</label>
              <input type="text" value={formDataset} onChange={(e) => setFormDataset(e.target.value)}
                placeholder="e.g. fct_orders"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }} />
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Kind</label>
              <select value={formKind} onChange={(e) => setFormKind(e.target.value as typeof formKind)}
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}>
                {METRIC_KINDS.map((k) => (<option key={k} value={k}>{k}</option>))}
              </select>
            </div>
            <div>
              <label className="block t-micro mb-1" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Description</label>
              <input type="text" value={formDescription} onChange={(e) => setFormDescription(e.target.value)}
                placeholder="Optional"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }} />
            </div>
          </div>
          {formError &&<p className="t-small" style={{ color: "var(--fail)" }}>{formError}</p>}
          <div className="flex items-center gap-2 pt-1">
            <button type="submit" disabled={submitting}
              className="px-4 py-1.5 t-small font-medium border transition-colors hover:opacity-90 disabled:opacity-40"
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}>
              {submitting ? "Creating..." : "Create metric"}
            </button>
            <button type="button" onClick={() => { setFormOpen(false); setFormError(null); }}
              className="px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-1)" }}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading && (
        <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
          <p className="t-small" style={{ color: "var(--fg-3)" }}>Loading metrics...</p>
        </div>
      )}
      {fetchError && (
        <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
          <p className="t-small" style={{ color: "var(--fail)" }}>{fetchError}</p>
        </div>
      )}

      {!loading && !fetchError && (
        <div className="border border-line" style={{ background: "var(--bg-1)" }}>
          {/* Active filter strip */}
          {hasActiveFilters && (
            <div className="flex items-center gap-2 px-3 py-1.5 border-b border-line" style={{ background: "var(--bg-0)" }}>
              <span className="t-micro" style={{ color: "var(--fg-3)" }}>Filtered:</span>
              {Object.entries(filterSets).map(([key, set]) =>
                set.size > 0 ? (
                  <span key={key} className="flex items-center gap-1 t-micro px-1.5 py-0.5 border border-line"
                        style={{ color: "var(--accent)" }}>
                    {key}: {Array.from(set).join(", ")}
                    <button onClick={() => updateFilter(key as MetricFilterKey, EMPTY_SET)} className="hover:opacity-70">
                      <X size={9} />
                    </button>
                  </span>
                ) : null
              )}
              <button onClick={clearAllFilters} className="t-micro hover:underline ml-1" style={{ color: "var(--fg-3)" }}>
                Clear all
              </button>
              <span className="t-micro ml-auto" style={{ color: "var(--fg-3)" }}>
                {filtered.length} of {metrics.length}
              </span>
            </div>
          )}

          {filtered.length === 0 ? (
            <div className="px-4 py-12 text-center t-small" style={{ color: "var(--fg-3)" }}>
              {hasActiveFilters ? "No metrics match the current filters." : "No metrics tracked yet."}
            </div>
          ) : (
            <table className="w-full" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr className="border-b border-line">
                  <th className="px-3 py-2" style={{ width: 36 }}>
                    <input ref={selectAllRef} type="checkbox"
                      checked={selectedFqns.size === filtered.length && filtered.length > 0}
                      onChange={toggleSelectAll}
                      style={checkboxStyle} />
                  </th>
                  <th className="px-3 py-2 text-left t-micro"
                      style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                    Metric
                  </th>
                  <FilterHeader label="Dataset" {...filterHeaderProps("dataset")} />
                  <FilterHeader label="Kind" {...filterHeaderProps("kind")} />
                  <FilterHeader label="Verdict" {...filterHeaderProps("verdict")} />
                  <th className="px-3 py-2" style={{ width: 80 }} />
                </tr>
              </thead>
              <tbody>
                {filtered.map((m) => {
                  const isSelected = selectedFqns.has(m.fqn);
                  const isEditing = editingRowFqn === m.fqn;
                  return (
                    <tr key={m.fqn} className="border-b border-line last:border-0 transition-colors"
                        style={{ background: isSelected ? "rgba(99,102,241,0.06)" : undefined }}>

                      {/* Checkbox */}
                      <td className="px-3 py-2" style={{ width: 36 }} onClick={(e) => e.stopPropagation()}>
                        <input type="checkbox" checked={isSelected} onChange={() => toggleSelect(m.fqn)} style={checkboxStyle} />
                      </td>

                      {/* Metric name + fqn */}
                      <td className="px-3 py-2">
                        {isEditing && editRow ? (
                          <input autoFocus value={editRow.display_name}
                            onChange={(e) => setEditRow({ ...editRow, display_name: e.target.value })}
                            className="t-small font-mono border border-accent outline-none px-2 py-0.5 w-full"
                            style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
                            onKeyDown={(e) => { if (e.key === "Escape") cancelEditRow(); if (e.key === "Enter") saveEditRow(m.fqn); }} />
                        ) : (
                          <>
                            <Link href={`/metrics/${encodeURIComponent(m.fqn)}`}
                              className="t-small font-mono hover:underline"
                              style={{ color: "var(--accent)" }}>
                              {m.display_name}
                            </Link>
                            <p className="t-micro mt-0.5 font-mono" style={{ color: "var(--fg-3)" }}>{m.fqn}</p>
                          </>
                        )}
                      </td>

                      {/* Dataset */}
                      <td className="px-3 py-2">
                        {isEditing && editRow ? (
                          <input value={editRow.dataset}
                            onChange={(e) => setEditRow({ ...editRow, dataset: e.target.value })}
                            className="t-micro font-mono border border-line outline-none px-2 py-0.5 w-full"
                            style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
                            onKeyDown={(e) => { if (e.key === "Escape") cancelEditRow(); if (e.key === "Enter") saveEditRow(m.fqn); }} />
                        ) : (
                          <span className="t-micro font-mono" style={{ color: "var(--fg-2)" }}>
                            {[m.source_id, m.dataset, m.column_name].filter(Boolean).join(" / ") || m.dataset}
                          </span>
                        )}
                      </td>

                      {/* Kind */}
                      <td className="px-2 py-1.5" onClick={(e) => e.stopPropagation()}>
                        {isEditing && editRow ? (
                          <select value={editRow.kind}
                            onChange={(e) => setEditRow({ ...editRow, kind: e.target.value })}
                            className="t-small font-mono border border-accent outline-none px-1 py-0.5"
                            style={{ background: "var(--bg-2)", color: "var(--accent)" }}>
                            {METRIC_KINDS.map((k) => (
                              <option key={k} value={k} title={KIND_HINT[k]}>{k}</option>
                            ))}
                          </select>
                        ) : (
                          <span className="t-small font-mono" style={{ color: "var(--fg-2)" }} title={KIND_HINT[m.kind] ?? m.kind}>
                            {m.kind}
                          </span>
                        )}
                      </td>

                      {/* Verdict */}
                      <td className="px-3 py-2">
                        {m.current_verdict ? (
                          <span className="t-micro font-mono px-1.5 py-0.5"
                                style={{
                                  color: VERDICT_COLOR[m.current_verdict] ?? "var(--fg-3)",
                                  background: (VERDICT_COLOR[m.current_verdict] ?? "var(--fg-3)") + "18",
                                }}>
                            {m.current_verdict}
                          </span>
                        ) : (
                          <span className="t-micro" style={{ color: "var(--fg-3)" }}>--</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-3 py-2 text-right" style={{ width: 80 }} onClick={(e) => e.stopPropagation()}>
                        {isEditing ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <button onClick={() => saveEditRow(m.fqn)} disabled={savingRow}
                              className="flex items-center gap-1 px-2 py-0.5 t-micro border transition-colors"
                              style={{ borderColor: "var(--accent)", color: "var(--accent)", background: "var(--accent-bg)" }}>
                              {savingRow ? <Loader2 size={10} strokeWidth={2} className="animate-spin" /> : <Check size={10} strokeWidth={2} />}
                              Save
                            </button>
                            <button onClick={cancelEditRow} className="t-micro px-1 hover:opacity-60" style={{ color: "var(--fg-3)" }}>✕</button>
                          </div>
                        ) : confirmDeleteFqn === m.fqn ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <button onClick={() => handleDeleteMetric(m.fqn)} disabled={deletingFqn}
                              className="flex items-center gap-1 px-2 py-0.5 t-micro border transition-colors"
                              style={{ borderColor: "var(--fail)", color: "var(--fail)", background: "rgba(224,123,110,0.08)" }}>
                              {deletingFqn ? <Loader2 size={10} strokeWidth={2} className="animate-spin" /> : "delete"}
                            </button>
                            <button onClick={() => setConfirmDeleteFqn(null)} className="t-micro px-1 hover:opacity-60" style={{ color: "var(--fg-3)" }}>✕</button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => startEditRow(m)}
                              className="inline-flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors"
                              style={{ color: "var(--fg-3)" }} title="Edit metric">
                              <Pencil size={11} strokeWidth={1.6} />
                            </button>
                            <button onClick={() => setConfirmDeleteFqn(m.fqn)}
                              className="inline-flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors"
                              style={{ color: "var(--fg-3)" }} title="Delete metric">
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
      )}
    </div>
  );
}

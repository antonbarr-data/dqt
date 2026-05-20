"use client";

import { useEffect, useState, useCallback } from "react";
import { ChevronRight, ChevronDown, Database, Table2, Plus, Columns, Trash2, Loader2 } from "lucide-react";
import { SuggestPanel } from "@/components/checks/suggest-panel";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Source {
  id: string;
  name: string;
  engine: string;
  tables: number;
  status: string;
}

interface Dataset {
  id: string;
  source: string;
  schema: string;
  row_count: number | null;
  column_count: number | null;
  check_count: number;
  status: string;
  last_run: string;
}

interface CheckResult {
  id: number;
  dataset_id: string;
  column: string | null;
  detector: string;
  score: number | null;
  verdict: string | null;
  message: string | null;
}

interface DatasetDetail extends Dataset {
  checks: CheckResult[];
}

interface ColumnCheck {
  id: string;
  dataset_id: string;
  column: string;
  detector_slug: string;
  params: Record<string, unknown>;
  rationale: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusColor(status: string | null | undefined): string {
  if (status === "pass") return "var(--pass)";
  if (status === "warn") return "var(--warn)";
  if (status === "fail") return "var(--fail)";
  return "var(--fg-3)";
}

function StatusDot({ status }: { status: string | null | undefined }) {
  const color = statusColor(status);
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        flexShrink: 0,
        background: color,
        boxShadow: `0 0 0 2px ${color}30`,
      }}
    />
  );
}

function SkeletonBar({ width = "100%", height = 14 }: { width?: string; height?: number }) {
  return (
    <div
      style={{
        width,
        height,
        background: "var(--bg-3)",
        opacity: 0.6,
        borderRadius: 0,
      }}
    />
  );
}

// Group datasets by schema within a source
function groupBySchema(datasets: Dataset[]): Record<string, Dataset[]> {
  const groups: Record<string, Dataset[]> = {};
  for (const ds of datasets) {
    const key = ds.schema || "(default)";
    if (!groups[key]) groups[key] = [];
    groups[key].push(ds);
  }
  return groups;
}

// Aggregate columns from detail checks (deduplicate by column name)
function extractColumns(checks: CheckResult[]): Array<{ name: string; verdict: string | null; checkCount: number }> {
  const map = new Map<string, { verdict: string | null; checkCount: number }>();
  for (const c of checks) {
    const col = c.column ?? "(table)";
    const existing = map.get(col);
    if (!existing) {
      map.set(col, { verdict: c.verdict, checkCount: 1 });
    } else {
      existing.checkCount += 1;
      // Escalate verdict
      if (c.verdict === "fail" || existing.verdict !== "fail") {
        if (c.verdict === "fail") existing.verdict = "fail";
        else if (c.verdict === "warn" && existing.verdict !== "fail") existing.verdict = "warn";
      }
    }
  }
  return Array.from(map.entries()).map(([name, meta]) => ({ name, ...meta }));
}

// ---------------------------------------------------------------------------
// Column expanded row
// ---------------------------------------------------------------------------

function ColumnExpanded({
  datasetId,
  column,
  onColumnDeleted,
}: {
  datasetId: string;
  column: string;
  onColumnDeleted?: () => void;
}) {
  const [checks, setChecks] = useState<ColumnCheck[]>([]);
  const [loading, setLoading] = useState(true);
  const [slug, setSlug] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [deletingColumn, setDeletingColumn] = useState(false);
  const [confirmDeleteCol, setConfirmDeleteCol] = useState(false);

  const loadChecks = useCallback(() => {
    setLoading(true);
    fetch(`/api/v1/datasets/${encodeURIComponent(datasetId)}/columns/${encodeURIComponent(column)}/checks`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: ColumnCheck[]) => setChecks(data))
      .catch(() => setChecks([]))
      .finally(() => setLoading(false));
  }, [datasetId, column]);

  useEffect(() => {
    loadChecks();
  }, [loadChecks]);

  function handleDeleteColumn() {
    setDeletingColumn(true);
    fetch(`/api/v1/datasets/${encodeURIComponent(datasetId)}/columns/${encodeURIComponent(column)}`, { method: "DELETE" })
      .then(() => { onColumnDeleted?.(); })
      .catch(() => setDeletingColumn(false))
      .finally(() => { setDeletingColumn(false); setConfirmDeleteCol(false); });
  }

  function handleAdd() {
    if (!slug.trim()) return;
    setAdding(true);
    setAddError(null);
    fetch(`/api/v1/datasets/${encodeURIComponent(datasetId)}/columns/${encodeURIComponent(column)}/checks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ detector_slug: slug.trim(), params: {}, rationale: "" }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(() => {
        setSlug("");
        loadChecks();
      })
      .catch((e: Error) => setAddError(e.message))
      .finally(() => setAdding(false));
  }

  return (
    <div
      style={{
        background: "var(--bg-2)",
        borderTop: "1px solid var(--line)",
        padding: "12px 16px 0",
      }}
    >
      {/* Existing checks */}
      <div className="mb-3">
        <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Checks
        </p>
        {loading ? (
          <SkeletonBar width="60%" height={12} />
        ) : checks.length === 0 ? (
          <p className="t-micro" style={{ color: "var(--fg-3)" }}>No checks yet.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {checks.map((c) => (
              <span
                key={c.id}
                className="t-micro px-2 py-0.5 border"
                style={{
                  borderColor: "var(--line-3)",
                  color: "var(--fg-1)",
                  fontFamily: "var(--font-jetbrains-mono)",
                  background: "var(--bg-3)",
                }}
              >
                {c.detector_slug}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Add check form */}
      <div className="flex items-center gap-2 mb-3">
        <input
          type="text"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="detector_slug"
          className="t-small flex-1 px-2 py-1 border"
          style={{
            background: "var(--bg-1)",
            borderColor: "var(--line)",
            color: "var(--fg-0)",
            fontFamily: "var(--font-jetbrains-mono)",
            outline: "none",
            minWidth: 0,
          }}
        />
        <button
          onClick={handleAdd}
          disabled={adding || !slug.trim()}
          className="t-micro px-3 py-1 border flex items-center gap-1"
          style={{
            borderColor: slug.trim() ? "var(--accent)" : "var(--line)",
            color: slug.trim() ? "var(--accent)" : "var(--fg-3)",
            background: "transparent",
            cursor: adding || !slug.trim() ? "default" : "pointer",
            flexShrink: 0,
          }}
        >
          <Plus size={11} strokeWidth={1.6} />
          {adding ? "Adding..." : "Add"}
        </button>
      </div>
      {addError && (
        <p className="t-micro mb-2" style={{ color: "var(--fail)" }}>
          {addError}
        </p>
      )}

      {/* AI suggestions */}
      <div>
        <p className="t-micro mb-1" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          AI Suggestions
        </p>
        <SuggestPanel datasetId={datasetId} column={column} />
      </div>

      {/* Delete column */}
      <div className="py-3 flex items-center justify-end gap-2">
        {confirmDeleteCol ? (
          <>
            <button
              onClick={handleDeleteColumn}
              disabled={deletingColumn}
              className="flex items-center gap-1 px-2 py-0.5 t-micro border transition-colors"
              style={{ borderColor: "var(--fail)", color: "var(--fail)", background: "rgba(224,123,110,0.08)" }}
            >
              {deletingColumn ? <Loader2 size={10} strokeWidth={2} className="animate-spin" /> : "remove column"}
            </button>
            <button
              onClick={() => setConfirmDeleteCol(false)}
              className="t-micro px-1 hover:opacity-60"
              style={{ color: "var(--fg-3)" }}
            >
              ✕
            </button>
          </>
        ) : (
          <button
            onClick={() => setConfirmDeleteCol(true)}
            className="t-micro flex items-center gap-1 hover:opacity-70 transition-opacity"
            style={{ color: "var(--fg-3)" }}
          >
            <Trash2 size={10} strokeWidth={1.6} />
            remove from monitoring
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DatasetsPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);

  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(true);
  const [datasetsError, setDatasetsError] = useState<string | null>(null);

  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set());

  const [datasetDetail, setDatasetDetail] = useState<DatasetDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [confirmDeleteDataset, setConfirmDeleteDataset] = useState<string | null>(null);
  const [deletingDataset, setDeletingDataset] = useState(false);

  // Load sources
  useEffect(() => {
    setSourcesLoading(true);
    setSourcesError(null);
    fetch("/api/v1/sources")
      .then((r) => (r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`)))
      .then((data: Source[]) => {
        setSources(data);
        if (data.length > 0) setSelectedSourceId(data[0].id);
      })
      .catch((e: unknown) => setSourcesError(String(e)))
      .finally(() => setSourcesLoading(false));
  }, []);

  // Load datasets
  useEffect(() => {
    setDatasetsLoading(true);
    setDatasetsError(null);
    fetch("/api/v1/datasets")
      .then((r) => (r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`)))
      .then((data: Dataset[]) => setDatasets(data))
      .catch((e: unknown) => setDatasetsError(String(e)))
      .finally(() => setDatasetsLoading(false));
  }, []);

  // Load dataset detail when selected
  useEffect(() => {
    if (!selectedDatasetId) {
      setDatasetDetail(null);
      return;
    }
    setDetailLoading(true);
    setDetailError(null);
    fetch(`/api/v1/datasets/${encodeURIComponent(selectedDatasetId)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`)))
      .then((data: DatasetDetail) => setDatasetDetail(data))
      .catch((e: unknown) => setDetailError(String(e)))
      .finally(() => setDetailLoading(false));
  }, [selectedDatasetId]);

  function handleDeleteDataset(datasetId: string) {
    setDeletingDataset(true);
    fetch(`/api/v1/datasets/${encodeURIComponent(datasetId)}`, { method: "DELETE" })
      .then(() => {
        setDatasets((prev) => prev.filter((d) => d.id !== datasetId));
        if (selectedDatasetId === datasetId) {
          setSelectedDatasetId(null);
          setDatasetDetail(null);
        }
      })
      .catch(() => {})
      .finally(() => { setDeletingDataset(false); setConfirmDeleteDataset(null); });
  }

  function handleColumnDeleted(col: string) {
    setDatasetDetail((prev) => {
      if (!prev) return prev;
      return { ...prev, checks: prev.checks.filter((c) => c.column !== col) };
    });
  }

  // When source selection changes, clear dataset selection
  function handleSelectSource(id: string) {
    setSelectedSourceId(id);
    setSelectedDatasetId(null);
    setDatasetDetail(null);
  }

  // Toggle schema group expand
  function toggleSchema(key: string) {
    setExpandedSchemas((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  // Datasets filtered to selected source
  const filteredDatasets = selectedSourceId
    ? datasets.filter((d) => d.source === selectedSourceId)
    : datasets;

  const schemaGroups = groupBySchema(filteredDatasets);

  // Auto-expand all schemas when source changes
  useEffect(() => {
    setExpandedSchemas(new Set(Object.keys(groupBySchema(filteredDatasets))));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSourceId, datasetsLoading]);

  return (
    <div
      className="flex h-full overflow-hidden fade-in"
      style={{ background: "var(--bg-0)" }}
    >
      {/* ----------------------------------------------------------------- */}
      {/* Left rail — sources (220px)                                        */}
      {/* ----------------------------------------------------------------- */}
      <div
        style={{
          width: 220,
          flexShrink: 0,
          borderRight: "1px solid var(--line)",
          background: "var(--bg-1)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <div
          className="px-3 py-3 border-b"
          style={{ borderColor: "var(--line)", flexShrink: 0 }}
        >
          <p
            className="t-micro"
            style={{
              color: "var(--fg-3)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Sources
          </p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sourcesLoading && (
            <div className="flex flex-col gap-2 p-3">
              {[1, 2, 3].map((i) => (
                <SkeletonBar key={i} width="80%" height={13} />
              ))}
            </div>
          )}
          {sourcesError && (
            <p className="t-micro px-3 py-3" style={{ color: "var(--fail)" }}>
              {sourcesError}
            </p>
          )}
          {!sourcesLoading && !sourcesError && sources.length === 0 && (
            <p className="t-small px-3 py-4 text-center" style={{ color: "var(--fg-3)" }}>
              No sources.
            </p>
          )}
          {!sourcesLoading &&
            !sourcesError &&
            sources.map((src) => {
              const isSelected = selectedSourceId === src.id;
              return (
                <button
                  key={src.id}
                  onClick={() => handleSelectSource(src.id)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-left transition-colors"
                  style={{
                    background: isSelected ? "var(--accent-bg)" : "transparent",
                    borderLeft: isSelected ? "2px solid var(--accent)" : "2px solid transparent",
                    cursor: "pointer",
                  }}
                >
                  <Database
                    size={13}
                    strokeWidth={1.6}
                    style={{ color: isSelected ? "var(--accent)" : "var(--fg-3)", flexShrink: 0 }}
                  />
                  <div className="flex-1 min-w-0">
                    <p
                      className="t-small truncate"
                      style={{
                        color: isSelected ? "var(--fg-0)" : "var(--fg-1)",
                        fontFamily: "var(--font-jetbrains-mono)",
                      }}
                    >
                      {src.name}
                    </p>
                    <p className="t-micro" style={{ color: "var(--fg-3)" }}>
                      {src.engine} · {src.tables ?? 0} tables
                    </p>
                  </div>
                  <StatusDot status={src.status} />
                </button>
              );
            })}
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Middle rail — schema/table tree (280px)                            */}
      {/* ----------------------------------------------------------------- */}
      <div
        style={{
          width: 280,
          flexShrink: 0,
          borderRight: "1px solid var(--line)",
          background: "var(--bg-1)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <div
          className="px-3 py-3 border-b flex items-center justify-between"
          style={{ borderColor: "var(--line)", flexShrink: 0 }}
        >
          <p
            className="t-micro"
            style={{
              color: "var(--fg-3)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Tables
          </p>
          {!datasetsLoading && (
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>
              {filteredDatasets.length}
            </span>
          )}
        </div>
        <div className="flex-1 overflow-y-auto">
          {datasetsLoading && (
            <div className="flex flex-col gap-2 p-3">
              {[1, 2, 3, 4].map((i) => (
                <SkeletonBar key={i} width={`${60 + i * 8}%`} height={12} />
              ))}
            </div>
          )}
          {datasetsError && (
            <p className="t-micro px-3 py-3" style={{ color: "var(--fail)" }}>
              {datasetsError}
            </p>
          )}
          {!datasetsLoading && !datasetsError && filteredDatasets.length === 0 && (
            <p className="t-small px-3 py-4 text-center" style={{ color: "var(--fg-3)" }}>
              {selectedSourceId ? "No datasets for this source." : "Select a source."}
            </p>
          )}
          {!datasetsLoading &&
            !datasetsError &&
            Object.entries(schemaGroups).map(([schema, schemaDatassets]) => {
              const isOpen = expandedSchemas.has(schema);
              return (
                <div key={schema}>
                  {/* Schema header */}
                  <button
                    onClick={() => toggleSchema(schema)}
                    className="w-full flex items-center gap-1.5 px-3 py-2 text-left border-b transition-colors"
                    style={{
                      borderColor: "var(--line)",
                      background: "var(--bg-2)",
                      cursor: "pointer",
                    }}
                  >
                    {isOpen ? (
                      <ChevronDown size={12} strokeWidth={1.6} style={{ color: "var(--fg-3)" }} />
                    ) : (
                      <ChevronRight size={12} strokeWidth={1.6} style={{ color: "var(--fg-3)" }} />
                    )}
                    <span
                      className="t-micro flex-1 truncate"
                      style={{
                        color: "var(--fg-2)",
                        fontFamily: "var(--font-jetbrains-mono)",
                        letterSpacing: "0.04em",
                      }}
                    >
                      {schema}
                    </span>
                    <span className="t-micro" style={{ color: "var(--fg-3)" }}>
                      {schemaDatassets.length}
                    </span>
                  </button>

                  {/* Dataset rows */}
                  {isOpen &&
                    schemaDatassets.map((ds) => {
                      const isSelected = selectedDatasetId === ds.id;
                      return (
                        <div
                          key={ds.id}
                          className="flex items-center border-b"
                          style={{
                            borderColor: "var(--line)",
                            background: isSelected ? "var(--accent-bg)" : "transparent",
                            borderLeft: isSelected ? "2px solid var(--accent)" : "2px solid transparent",
                          }}
                        >
                          <button
                            onClick={() => setSelectedDatasetId(ds.id)}
                            className="flex-1 flex items-center gap-2 pl-6 pr-2 py-2 text-left transition-colors"
                            style={{ cursor: "pointer", minWidth: 0 }}
                          >
                            <Table2
                              size={12}
                              strokeWidth={1.6}
                              style={{
                                color: isSelected ? "var(--accent)" : "var(--fg-3)",
                                flexShrink: 0,
                              }}
                            />
                            <span
                              className="t-small flex-1 truncate"
                              style={{
                                color: isSelected ? "var(--fg-0)" : "var(--fg-1)",
                                fontFamily: "var(--font-jetbrains-mono)",
                              }}
                            >
                              {ds.id}
                            </span>
                            <StatusDot status={ds.status} />
                            <span className="t-micro" style={{ color: "var(--fg-3)" }}>
                              {ds.column_count ?? "--"}
                            </span>
                          </button>
                          <div className="px-1 flex items-center" onClick={(e) => e.stopPropagation()}>
                            {confirmDeleteDataset === ds.id ? (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleDeleteDataset(ds.id)}
                                  disabled={deletingDataset}
                                  className="t-micro px-1.5 py-0.5 border transition-colors"
                                  style={{ borderColor: "var(--fail)", color: "var(--fail)", background: "rgba(224,123,110,0.08)" }}
                                >
                                  {deletingDataset ? <Loader2 size={9} strokeWidth={2} className="animate-spin" /> : "del"}
                                </button>
                                <button
                                  onClick={() => setConfirmDeleteDataset(null)}
                                  className="t-micro hover:opacity-60"
                                  style={{ color: "var(--fg-3)" }}
                                >
                                  ✕
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setConfirmDeleteDataset(ds.id)}
                                className="w-5 h-5 flex items-center justify-center border border-transparent hover:border-line transition-colors"
                                style={{ color: "var(--fg-3)" }}
                                title="Remove dataset"
                              >
                                <Trash2 size={10} strokeWidth={1.6} />
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                </div>
              );
            })}
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Main panel — column list                                           */}
      {/* ----------------------------------------------------------------- */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <div
          className="flex items-center gap-2 px-4 py-3 border-b"
          style={{
            borderColor: "var(--line)",
            background: "var(--bg-1)",
            flexShrink: 0,
          }}
        >
          {datasetDetail ? (
            <>
              <Columns
                size={14}
                strokeWidth={1.6}
                style={{ color: "var(--fg-3)" }}
              />
              <span
                className="t-small"
                style={{
                  color: "var(--fg-0)",
                  fontFamily: "var(--font-jetbrains-mono)",
                }}
              >
                {datasetDetail.id}
              </span>
              <span className="t-micro" style={{ color: "var(--fg-3)" }}>
                {extractColumns(datasetDetail.checks).length} columns
              </span>
            </>
          ) : (
            <span className="t-small" style={{ color: "var(--fg-3)" }}>
              Select a dataset
            </span>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto" style={{ background: "var(--bg-0)" }}>
          {detailLoading && (
            <div className="flex flex-col gap-2 p-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <SkeletonBar key={i} width={`${50 + i * 7}%`} height={14} />
              ))}
            </div>
          )}
          {detailError && (
            <div className="flex items-center justify-center h-32">
              <p className="t-small" style={{ color: "var(--fail)" }}>
                {detailError}
              </p>
            </div>
          )}
          {!selectedDatasetId && !detailLoading && (
            <div className="flex items-center justify-center h-32">
              <p className="t-small" style={{ color: "var(--fg-3)" }}>
                Select a dataset to browse columns
              </p>
            </div>
          )}
          {!detailLoading && !detailError && datasetDetail && (
            <ColumnList dataset={datasetDetail} onColumnDeleted={handleColumnDeleted} />
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Column list component (separated to isolate expanded state)
// ---------------------------------------------------------------------------

function ColumnList({ dataset, onColumnDeleted }: { dataset: DatasetDetail; onColumnDeleted?: (col: string) => void }) {
  const [expandedCol, setExpandedCol] = useState<string | null>(null);
  const columns = extractColumns(dataset.checks);

  return (
    <>
      {columns.length === 0 ? (
        <div className="flex items-center justify-center h-32">
          <p className="t-small" style={{ color: "var(--fg-3)" }}>
            No columns found.
          </p>
        </div>
      ) : (
        columns.map((col) => {
          const isExpanded = expandedCol === col.name;
          return (
            <div key={col.name} style={{ borderBottom: "1px solid var(--line)" }}>
              <button
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left"
                style={{
                  background: isExpanded ? "var(--bg-2)" : "transparent",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  if (!isExpanded)
                    (e.currentTarget as HTMLButtonElement).style.background = "var(--bg-1)";
                }}
                onMouseLeave={(e) => {
                  if (!isExpanded)
                    (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                }}
                onClick={() => setExpandedCol(isExpanded ? null : col.name)}
              >
                {isExpanded ? (
                  <ChevronDown
                    size={13}
                    strokeWidth={1.6}
                    style={{ color: "var(--fg-3)", flexShrink: 0 }}
                  />
                ) : (
                  <ChevronRight
                    size={13}
                    strokeWidth={1.6}
                    style={{ color: "var(--fg-3)", flexShrink: 0 }}
                  />
                )}
                <StatusDot status={col.verdict ?? undefined} />
                <span
                  className="t-small flex-1 min-w-0 truncate"
                  style={{
                    color: "var(--fg-0)",
                    fontFamily: "var(--font-jetbrains-mono)",
                  }}
                >
                  {col.name}
                </span>
                {col.checkCount > 0 && (
                  <span
                    className="t-micro px-1.5"
                    style={{
                      background: "var(--bg-3)",
                      color: "var(--fg-3)",
                      fontFamily: "var(--font-jetbrains-mono)",
                      flexShrink: 0,
                    }}
                  >
                    {col.checkCount}
                  </span>
                )}
              </button>
              {isExpanded && (
                <ColumnExpanded
                  datasetId={dataset.id}
                  column={col.name}
                  onColumnDeleted={() => {
                    setExpandedCol(null);
                    onColumnDeleted?.(col.name);
                  }}
                />
              )}
            </div>
          );
        })
      )}
    </>
  );
}

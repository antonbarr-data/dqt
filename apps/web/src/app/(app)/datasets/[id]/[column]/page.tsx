"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { Loader2, Plus, Trash2, RefreshCw } from "lucide-react";

import { TimeSeriesPanel } from "@/components/column-profile/time-series-panel";
import { CompletenessPanel } from "@/components/column-profile/completeness-panel";
import { DistributionPanel } from "@/components/column-profile/distribution-panel";
import { TopValuesPanel } from "@/components/column-profile/top-values-panel";
import { SeasonalityPanel } from "@/components/column-profile/seasonality-panel";
import { SchemaPanel } from "@/components/column-profile/schema-panel";
import { LineagePanel } from "@/components/column-profile/lineage-panel";
import { IncidentsPanel } from "@/components/column-profile/incidents-panel";

const SuggestPanel = dynamic(
  () => import("@/components/checks/suggest-panel").then(m => m.SuggestPanel),
  { ssr: false, loading: () => <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>Loading...</div> }
);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ColumnStats {
  computed_at: string;
  kind: string;
  data_type: string | null;
  nullable: boolean | null;
  position: number | null;
  total_count: number | null;
  null_count: number | null;
  zero_count: number | null;
  empty_count: number | null;
  distinct_count: number | null;
  p_min: number | null;
  p_max: number | null;
  p_mean: number | null;
  p_stddev: number | null;
  p2: number | null; p5: number | null; p10: number | null;
  p25: number | null; p50: number | null; p75: number | null;
  p90: number | null; p95: number | null; p98: number | null; p99: number | null;
  histogram: Array<{ lower: number; upper: number; count: number; is_outlier: boolean }>;
  top_values: Array<{ value: string; count: number; pct: number }>;
}

interface SchemaVersion {
  id: number;
  data_type: string | null;
  nullable: boolean | null;
  position: number | null;
  recorded_at: string;
}

interface RunPoint {
  id: number;
  detector: string;
  score: number | null;
  verdict: string | null;
  ran_at: string;
}

interface ColumnCheck {
  id: string;
  dataset_id: string;
  column: string;
  detector_slug: string;
  params: Record<string, unknown>;
  rationale: string;
  enabled: boolean;
}

interface Incident {
  id: number;
  detector_slug: string;
  severity: string;
  message: string;
  status: string;
  opened_at: string;
  resolved_at: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DETECTOR_CAT: Record<string, string> = {
  completeness: "completeness", null_fraction: "completeness", volume: "completeness",
  volume_anomaly: "completeness", freshness_seconds_behind: "completeness",
  uniqueness: "validity", validity: "validity", set_membership: "validity",
  set_exclusion: "validity", regex_match: "validity", value_in_range: "validity",
  string_length_range: "validity", date_format: "validity", string_case: "validity",
  sql_assertion: "validity", referential_integrity_rate: "validity",
  referential_integrity: "validity", column_pair: "validity", composite_uniqueness: "validity",
  ks_pvalue: "drift", ks_drift: "drift", wasserstein_1: "drift", psi: "drift",
  kl_divergence: "drift", js_divergence: "drift", chi_square_drift: "drift",
  cramers_v: "drift", mmd: "drift", mutual_information: "drift", benford_law_fit: "drift",
  mad_outlier_fraction: "outliers", double_mad_outlier_fraction: "outliers",
  zscore_outlier_fraction: "outliers", adjusted_boxplot_fraction: "outliers",
  iqr_fence: "outliers", grubbs: "outliers", generalized_esd: "outliers",
  stl_residual_zscore: "timeseries", cusum: "timeseries", page_hinkley: "timeseries",
  holt_winters: "timeseries", prophet_anomaly: "timeseries",
};

const CAT_COLOR: Record<string, string> = {
  completeness: "var(--pass)",
  validity: "var(--accent)",
  drift: "var(--warn)",
  outliers: "var(--fail)",
  timeseries: "#9b8fff",
  custom: "var(--fg-3)",
};

const VERDICT_COLOR: Record<string, string> = {
  pass: "var(--pass)", warn: "var(--warn)", fail: "var(--fail)",
  error: "var(--fail)", pending: "var(--fg-3)",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function detectorColor(slug: string): string {
  return CAT_COLOR[DETECTOR_CAT[slug] ?? "custom"] ?? "var(--fg-3)";
}

function fmtNum(v: number | null): string {
  if (v === null) return "--";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
}

function fmtPct(v: number | null, decimals = 1): string {
  if (v === null) return "--";
  return `${(v * 100).toFixed(decimals)}%`;
}

function fmtFloat(v: number | null, d = 4): string {
  if (v === null) return "--";
  return v.toFixed(d);
}

// ---------------------------------------------------------------------------
// VerdictBadge
// ---------------------------------------------------------------------------

function VerdictBadge({ verdict }: { verdict: string }) {
  const color = VERDICT_COLOR[verdict] ?? "var(--fg-3)";
  const bg =
    verdict === "fail" ? "var(--fail-bg)" :
    verdict === "warn" ? "rgba(217,181,102,0.12)" :
    verdict === "pass" ? "rgba(127,179,148,0.12)" :
    "var(--bg-2)";
  return (
    <span className="t-micro px-2 py-0.5" style={{ background: bg, color, fontFamily: "var(--font-jetbrains-mono)" }}>
      {verdict.toUpperCase()}
    </span>
  );
}

// ---------------------------------------------------------------------------
// TypeBadge
// ---------------------------------------------------------------------------

function TypeBadge({ kind, dataType }: { kind: string; dataType: string | null }) {
  const label = dataType ?? kind;
  const color = kind === "numeric" ? "var(--accent)" : kind === "categorical" ? "#9b8fff" : "var(--fg-3)";
  return (
    <span className="t-micro px-2 py-0.5 font-mono" style={{
      background: "var(--bg-2)", color,
      border: "1px solid var(--line)",
      fontFamily: "var(--font-jetbrains-mono)",
    }}>
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// PanelShell
// ---------------------------------------------------------------------------

function PanelShell({ title, right, children }: {
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          {title}
        </span>
        {right}
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// StatsSidebarPanel (inline)
// ---------------------------------------------------------------------------

function StatsSidebarPanel({ stats }: { stats: ColumnStats | null }) {
  if (!stats) {
    return (
      <PanelShell title="Profile stats">
        <div className="px-4 py-4 t-small" style={{ color: "var(--fg-3)" }}>No profile data yet.</div>
      </PanelShell>
    );
  }

  const nullPct = stats.total_count ? (stats.null_count ?? 0) / stats.total_count : null;
  const distinctPct = stats.total_count && stats.distinct_count !== null
    ? stats.distinct_count / stats.total_count
    : null;

  type Row = { label: string; value: string; sub?: string };
  const rows: Row[] = [
    { label: "Total rows", value: fmtNum(stats.total_count) },
    {
      label: "Null %",
      value: fmtPct(nullPct),
      sub: stats.null_count !== null ? `${fmtNum(stats.null_count)} rows` : undefined,
    },
    {
      label: "Distinct",
      value: fmtNum(stats.distinct_count),
      sub: distinctPct !== null ? `${fmtPct(distinctPct)} unique` : undefined,
    },
  ];

  if (stats.kind === "numeric") {
    rows.push(
      { label: "Mean", value: fmtFloat(stats.p_mean) },
      { label: "Std dev", value: fmtFloat(stats.p_stddev) },
      { label: "Min", value: fmtFloat(stats.p_min) },
      { label: "Median", value: fmtFloat(stats.p50) },
      { label: "Max", value: fmtFloat(stats.p_max) },
    );
  } else {
    const emptyPct = stats.total_count && stats.empty_count !== null
      ? stats.empty_count / stats.total_count
      : null;
    rows.push({ label: "Empty %", value: fmtPct(emptyPct) });
  }

  return (
    <PanelShell
      title="Profile stats"
      right={
        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
          {new Date(stats.computed_at).toLocaleDateString()}
        </span>
      }
    >
      {rows.map(({ label, value, sub }) => (
        <div
          key={label}
          className="px-4 py-2.5 flex items-center justify-between border-b border-line last:border-0"
        >
          <span className="t-small" style={{ color: "var(--fg-3)" }}>{label}</span>
          <div className="text-right">
            <span className="t-small font-mono" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>
              {value}
            </span>
            {sub && (
              <span className="t-micro block font-mono" style={{ color: "var(--fg-3)" }}>{sub}</span>
            )}
          </div>
        </div>
      ))}
    </PanelShell>
  );
}

// ---------------------------------------------------------------------------
// ActiveChecksPanel (inline)
// ---------------------------------------------------------------------------

function ActiveChecksPanel({
  checks, history, datasetId, column, onDeleted, onAdded,
}: {
  checks: ColumnCheck[];
  history: RunPoint[];
  datasetId: string;
  column: string;
  onDeleted: (id: string) => void;
  onAdded: (c: ColumnCheck) => void;
}) {
  const [showSuggest, setShowSuggest] = useState(false);

  const latestByDetector = useMemo(() => {
    const m = new Map<string, RunPoint>();
    for (const r of [...history].sort((a, b) => new Date(b.ran_at).getTime() - new Date(a.ran_at).getTime())) {
      if (!m.has(r.detector)) m.set(r.detector, r);
    }
    return m;
  }, [history]);

  async function handleDelete(checkId: string) {
    await fetch(`/api/v1/checks/${encodeURIComponent(checkId)}`, { method: "DELETE" });
    onDeleted(checkId);
  }

  return (
    <PanelShell
      title="Active checks"
      right={
        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{checks.length}</span>
      }
    >
      {checks.length === 0 ? (
        <div className="px-4 py-4 t-small" style={{ color: "var(--fg-3)" }}>No checks defined.</div>
      ) : (
        checks.map(chk => {
          const run = latestByDetector.get(chk.detector_slug);
          const verdict = run?.verdict ?? "pending";
          const score = run?.score ?? null;
          return (
            <div
              key={chk.id}
              className="px-4 py-2 flex items-center gap-2 border-b border-line last:border-0"
              style={{ background: verdict === "fail" ? "var(--fail-bg)" : undefined }}
            >
              <div style={{ width: 5, height: 5, background: detectorColor(chk.detector_slug), flexShrink: 0 }} />
              <span className="t-small font-mono truncate flex-1 min-w-0" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>
                {chk.detector_slug}
              </span>
              {score !== null && (
                <span className="t-micro font-mono flex-shrink-0" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
                  {(score * 100).toFixed(1)}%
                </span>
              )}
              <VerdictBadge verdict={verdict} />
              <button
                onClick={() => handleDelete(chk.id)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--fg-3)", padding: "2px 4px", flexShrink: 0 }}
                title="Delete check"
              >
                <Trash2 size={11} strokeWidth={1.5} />
              </button>
            </div>
          );
        })
      )}
      <div className="border-t border-line">
        <button
          onClick={() => setShowSuggest(v => !v)}
          className="w-full px-4 py-2.5 flex items-center gap-2 hover:opacity-80 transition-colors"
          style={{ background: "none", border: "none", cursor: "pointer", textAlign: "left" }}
        >
          <Plus size={12} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
          <span className="t-micro" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Add checks
          </span>
        </button>
        {showSuggest && (
          <div className="border-t border-line">
            <SuggestPanel
              datasetId={datasetId}
              column={column}
              existingChecks={checks}
              onCheckAdded={c => onAdded(c as ColumnCheck)}
              onCheckDeleted={id => onDeleted(id)}
            />
          </div>
        )}
      </div>
    </PanelShell>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ColumnProfilePage() {
  const params = useParams<{ id: string; column: string }>();
  const datasetId = decodeURIComponent(params.id);
  const column = decodeURIComponent(params.column);

  const [stats, setStats] = useState<ColumnStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [schemaHistory, setSchemaHistory] = useState<SchemaVersion[]>([]);
  const [history, setHistory] = useState<RunPoint[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [checks, setChecks] = useState<ColumnCheck[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const enc = encodeURIComponent;
  const base = `/api/v1/datasets/${enc(datasetId)}/columns/${enc(column)}`;

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const r = await fetch(`${base}/stats`);
      if (r.ok) {
        setStats(await r.json());
      } else {
        const body = await r.json().catch(() => ({}));
        setStatsError(body?.detail ?? `Error ${r.status}`);
      }
    } catch (e) {
      setStatsError(String(e));
    }
    setStatsLoading(false);
  }, [base]);

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const r = await fetch(`${base}/history`);
      if (r.ok) setHistory(await r.json());
    } catch { /* ignore */ }
    setHistoryLoading(false);
  }, [base]);

  const fetchChecks = useCallback(async () => {
    try {
      const r = await fetch(`${base}/checks`);
      if (r.ok) setChecks(await r.json());
    } catch { /* ignore */ }
  }, [base]);

  const fetchSchemaHistory = useCallback(async () => {
    try {
      const r = await fetch(`${base}/schema-history`);
      if (r.ok) setSchemaHistory(await r.json());
    } catch { /* ignore */ }
  }, [base]);

  const fetchIncidents = useCallback(async () => {
    try {
      const r = await fetch(`${base}/incidents`);
      if (r.ok) setIncidents(await r.json());
    } catch { /* ignore */ }
  }, [base]);

  useEffect(() => {
    fetchStats();
    fetchHistory();
    fetchChecks();
    fetchSchemaHistory();
    fetchIncidents();
  }, [fetchStats, fetchHistory, fetchChecks, fetchSchemaHistory, fetchIncidents]);

  async function handleRefresh() {
    setRefreshing(true);
    setStatsError(null);
    try {
      const r = await fetch(`${base}/refresh-stats`, { method: "POST" });
      if (r.ok) {
        setStats(await r.json());
      } else {
        const body = await r.json().catch(() => ({}));
        setStatsError(body?.detail ?? `Error ${r.status}`);
      }
    } catch (e) {
      setStatsError(String(e));
    }
    setRefreshing(false);
  }

  const worstVerdict = useMemo(() => {
    const latestByDet = new Map<string, RunPoint>();
    for (const r of [...history].sort((a, b) => new Date(b.ran_at).getTime() - new Date(a.ran_at).getTime())) {
      if (!latestByDet.has(r.detector)) latestByDet.set(r.detector, r);
    }
    const RANK: Record<string, number> = { fail: 3, error: 3, warn: 2, pass: 1 };
    let worst: string | null = null;
    for (const r of Array.from(latestByDet.values())) {
      const v = r.verdict ?? "pending";
      if (!worst || (RANK[v] ?? 0) > (RANK[worst] ?? 0)) worst = v;
    }
    return worst ?? "pending";
  }, [history]);

  const dqtScore = useMemo(() => {
    const latestByDet = new Map<string, RunPoint>();
    for (const r of [...history].sort((a, b) => new Date(b.ran_at).getTime() - new Date(a.ran_at).getTime())) {
      if (!latestByDet.has(r.detector)) latestByDet.set(r.detector, r);
    }
    const SCORE: Record<string, number> = { pass: 100, warn: 50, fail: 0, error: 0 };
    let min: number | null = null;
    for (const r of Array.from(latestByDet.values())) {
      const s = SCORE[r.verdict ?? ""];
      if (s !== undefined && (min === null || s < min)) min = s;
    }
    return min;
  }, [history]);

  const loading = statsLoading || historyLoading;

  return (
    <div className="flex flex-col h-full overflow-auto">
      <div className="p-5" style={{ maxWidth: 1400 }}>
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mb-4">
          <Link
            href="/datasets"
            className="t-small flex items-center gap-1.5 hover:opacity-80 transition-colors"
            style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}
          >
            <span style={{ fontSize: 13, lineHeight: 1 }}>←</span>
            Datasets
          </Link>
          <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
          <Link
            href={`/datasets/${enc(datasetId)}` as never}
            className="t-small font-mono hover:opacity-80 transition-colors truncate"
            style={{ color: "var(--accent)", maxWidth: 280 }}
          >
            {datasetId}
          </Link>
          <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
          <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{column}</span>
        </div>

        {/* Header */}
        <div className="flex items-center gap-3 flex-wrap mb-5">
          <h1
            className="font-mono"
            style={{ fontSize: 22, fontWeight: 300, color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", letterSpacing: "-0.02em" }}
          >
            <span style={{ color: "var(--fg-3)" }}>{datasetId}.</span>{column}
          </h1>
          {stats && <TypeBadge kind={stats.kind} dataType={stats.data_type} />}
          {stats?.position !== null && stats?.position !== undefined && (
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>pos {stats.position}</span>
          )}
          {stats?.total_count !== null && stats?.total_count !== undefined && (
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{fmtNum(stats.total_count)} rows</span>
          )}
          {!historyLoading && <VerdictBadge verdict={worstVerdict} />}
          {!historyLoading && dqtScore !== null && (
            <div className="flex items-center gap-1.5" style={{ borderLeft: "1px solid var(--line)", paddingLeft: 12 }}>
              <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>DQT</span>
              <span
                className="font-mono"
                style={{
                  fontSize: 16, fontWeight: 300,
                  color: dqtScore >= 80 ? "var(--pass)" : dqtScore >= 50 ? "var(--warn)" : "var(--fail)",
                  fontFamily: "var(--font-jetbrains-mono)",
                }}
              >
                {dqtScore}
              </span>
            </div>
          )}
          {loading && <Loader2 size={13} className="animate-spin" style={{ color: "var(--fg-3)" }} />}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 hover:opacity-80 transition-colors"
            style={{ background: "var(--bg-2)", border: "1px solid var(--line)", cursor: "pointer", color: "var(--fg-2)" }}
          >
            <RefreshCw size={11} strokeWidth={1.5} className={refreshing ? "animate-spin" : ""} />
            <span className="t-micro">Refresh profile</span>
          </button>
        </div>

        {/* Two-column layout */}
        <div className="flex gap-4 items-start">
          {/* Left column */}
          <div className="flex flex-col gap-4" style={{ flex: "1 1 0", minWidth: 0 }}>
            <TimeSeriesPanel history={history} schemaHistory={schemaHistory} />
            {statsError && (
              <div className="border border-line px-4 py-3 t-small" style={{ background: "var(--fail-bg)", color: "var(--fail)" }}>
                Profile error: {statsError}
              </div>
            )}
            <CompletenessPanel stats={stats} history={history} />
            <DistributionPanel stats={stats} />
            <TopValuesPanel stats={stats} />
            <SeasonalityPanel history={history} />
          </div>

          {/* Right sidebar */}
          <div className="flex flex-col gap-4" style={{ width: 340, flexShrink: 0 }}>
            <StatsSidebarPanel stats={stats} />
            <ActiveChecksPanel
              checks={checks}
              history={history}
              datasetId={datasetId}
              column={column}
              onDeleted={id => setChecks(prev => prev.filter(c => c.id !== id))}
              onAdded={c => setChecks(prev => [...prev, c])}
            />
            <SchemaPanel stats={stats} schemaHistory={schemaHistory} />
            <LineagePanel datasetId={datasetId} column={column} />
            <IncidentsPanel incidents={incidents} />
          </div>
        </div>
      </div>
    </div>
  );
}

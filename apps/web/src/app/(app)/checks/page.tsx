"use client";

import { useState, useEffect, useCallback } from "react";
import { Check, Sparkles, X, Play, CalendarClock, Loader2, Trash2 } from "lucide-react";
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
  score: number;
  verdict: Verdict;
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

type Verdict = "pass" | "warn" | "fail";
type Cadence = "hourly" | "daily" | "weekly" | "monthly";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORIES = [
  { label: "All",                   group: null,             hint: "Every check across all categories" },
  { label: "Completeness",          group: "completeness",   hint: "Is the data there?" },
  { label: "Validity",              group: "validity",       hint: "Does it match the rules?" },
  { label: "Integrity",             group: "integrity",      hint: "Is it internally consistent?" },
  { label: "Schema",                group: "schema",         hint: "Has the shape changed?" },
  { label: "Univariate outliers",   group: "outliers_uni",   hint: "Are individual values unusual?" },
  { label: "Multivariate outliers", group: "outliers_multi", hint: "Are rows unusual in combination?" },
  { label: "Drift",                 group: "drift",          hint: "Has the distribution shifted?" },
  { label: "Time series",           group: "timeseries",     hint: "Did the temporal pattern change?" },
  { label: "Custom",                group: "custom",         hint: "Specialized cases" },
] as const;

type CategoryLabel = typeof CATEGORIES[number]["label"];

const DETECTOR_GROUP: Record<string, string> = {
  null_fraction: "completeness", completeness: "completeness", row_count_in_range: "custom",
  value_in_range: "validity", referential_integrity: "integrity",
  schema_changed: "schema", column_added: "schema", column_removed: "schema",
  mad_outlier_fraction: "outliers_uni", adjusted_boxplot_fraction: "outliers_uni",
  zscore_fraction: "outliers_uni", grubbs: "outliers_uni", generalized_esd: "outliers_uni",
  mahalanobis_fraction: "outliers_multi", isolation_forest: "outliers_multi", lof: "outliers_multi",
  ks2sample: "drift", psi: "drift", wasserstein: "drift", jensenshannon: "drift",
  stl_residual_zscore: "timeseries", bocpd: "timeseries", cusum: "timeseries",
  holt_winters: "timeseries", prophet: "timeseries",
};

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function apiToRow(raw: {
  id: number; dataset_id: string; column: string | null;
  detector: string; verdict: string; score?: number;
}): CheckRow {
  return {
    id: String(raw.id),
    group: DETECTOR_GROUP[raw.detector] ?? "custom",
    dataset: raw.dataset_id,
    column: raw.column ?? "(table)",
    check: raw.detector,
    score: raw.score ?? 0,
    verdict: (raw.verdict as Verdict) ?? "pass",
  };
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
    const days = s.days_of_week.length
      ? s.days_of_week.map(d => DAY_LABELS[d]).join(", ")
      : "every day";
    return `Weekly on ${days} at ${time}`;
  }
  return `Monthly on day ${s.day_of_month} at ${time}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusDot({ verdict }: { verdict: Verdict }) {
  const color =
    verdict === "pass" ? "var(--pass)" : verdict === "warn" ? "var(--warn)" : "var(--fail)";
  return (
    <span style={{
      display: "inline-block", width: 7, height: 7,
      background: color, boxShadow: `0 0 0 2px ${color}28`, flexShrink: 0,
    }} />
  );
}

function YamlBlock({ code }: { code: string }) {
  return (
    <pre
      className="t-micro font-mono overflow-x-auto p-2.5"
      style={{ background: "var(--bg-0)", color: "var(--fg-1)", border: "1px solid var(--line)", whiteSpace: "pre", lineHeight: 1.6 }}
    >
      {code}
    </pre>
  );
}

// ---------------------------------------------------------------------------
// Schedule Modal
// ---------------------------------------------------------------------------

function ScheduleModal({
  schedules,
  onClose,
  onCreated,
  onDeleted,
  onToggled,
}: {
  schedules: Schedule[];
  onClose: () => void;
  onCreated: (s: Schedule) => void;
  onDeleted: (id: number) => void;
  onToggled: (s: Schedule) => void;
}) {
  const [cadence, setCadence] = useState<Cadence>("daily");
  const [runHour, setRunHour] = useState(9);
  const [runMinute, setRunMinute] = useState(0);
  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4, 5]); // Mon-Fri
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
        body: JSON.stringify({
          cadence,
          run_hour: runHour,
          run_minute: runMinute,
          days_of_week: cadence === "weekly" ? selectedDays : [],
          day_of_month: cadence === "monthly" ? dayOfMonth : 1,
        }),
      });
      if (res.ok) onCreated(await res.json());
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    setDeletingId(id);
    try {
      await fetch(`/api/v1/schedules/${id}`, { method: "DELETE" });
      onDeleted(id);
    } finally {
      setDeletingId(null);
    }
  }

  async function handleToggle(s: Schedule) {
    const res = await fetch(`/api/v1/schedules/${s.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !s.enabled }),
    });
    if (res.ok) onToggled(await res.json());
  }

  const selectStyle = {
    background: "var(--bg-2)", color: "var(--fg-0)",
    border: "1px solid var(--line)", padding: "4px 8px",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.55)" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="border border-line" style={{ background: "var(--bg-1)", width: 520, maxHeight: "90vh", overflowY: "auto" }}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="t-h3" style={{ color: "var(--fg-0)" }}>Check Schedule</span>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-6 h-6 border border-line hover:bg-bg-2 transition-colors"
            style={{ color: "var(--fg-2)" }}
          >
            <X size={12} strokeWidth={1.6} />
          </button>
        </div>

        <div className="p-4 space-y-5">
          {/* Frequency selector */}
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Frequency</p>
            <div className="flex gap-1.5">
              {(["hourly", "daily", "weekly", "monthly"] as Cadence[]).map(c => (
                <button
                  key={c}
                  onClick={() => setCadence(c)}
                  className="px-3 py-1.5 t-small border transition-colors capitalize"
                  style={{
                    borderColor: cadence === c ? "var(--accent)" : "var(--line)",
                    color: cadence === c ? "var(--accent)" : "var(--fg-1)",
                    background: cadence === c ? "var(--accent-bg)" : "var(--bg-2)",
                  }}
                >
                  {c.charAt(0).toUpperCase() + c.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Time picker — hidden for hourly */}
          {cadence !== "hourly" && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Run at</p>
              <div className="flex items-center gap-2">
                <select
                  value={runHour}
                  onChange={e => setRunHour(Number(e.target.value))}
                  className="t-small font-mono"
                  style={selectStyle}
                >
                  {HOURS.map(h => (
                    <option key={h} value={h}>{String(h).padStart(2, "0")}</option>
                  ))}
                </select>
                <span className="t-small" style={{ color: "var(--fg-2)" }}>:</span>
                <select
                  value={runMinute}
                  onChange={e => setRunMinute(Number(e.target.value))}
                  className="t-small font-mono"
                  style={selectStyle}
                >
                  {MINUTES.map(m => (
                    <option key={m} value={m}>{String(m).padStart(2, "0")}</option>
                  ))}
                </select>
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>UTC</span>
              </div>
            </div>
          )}

          {/* Hourly: minute picker */}
          {cadence === "hourly" && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>At minute</p>
              <div className="flex items-center gap-2">
                <span className="t-small font-mono" style={{ color: "var(--fg-3)" }}>:&nbsp;</span>
                <select
                  value={runMinute}
                  onChange={e => setRunMinute(Number(e.target.value))}
                  className="t-small font-mono"
                  style={selectStyle}
                >
                  {MINUTES.map(m => (
                    <option key={m} value={m}>{String(m).padStart(2, "0")}</option>
                  ))}
                </select>
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>past each hour</span>
              </div>
            </div>
          )}

          {/* Day-of-week picker */}
          {cadence === "weekly" && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Repeat on</p>
              <div className="flex gap-1.5">
                {DAY_LABELS.map((label, i) => {
                  const active = selectedDays.includes(i);
                  return (
                    <button
                      key={i}
                      onClick={() => toggleDay(i)}
                      className="w-10 py-1.5 t-micro border transition-colors"
                      style={{
                        borderColor: active ? "var(--accent)" : "var(--line)",
                        color: active ? "var(--accent)" : "var(--fg-2)",
                        background: active ? "var(--accent-bg)" : "var(--bg-2)",
                        fontFamily: "var(--font-jetbrains-mono)",
                      }}
                    >
                      {label.slice(0, 2)}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Day-of-month picker */}
          {cadence === "monthly" && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Day of month</p>
              <select
                value={dayOfMonth}
                onChange={e => setDayOfMonth(Number(e.target.value))}
                className="t-small font-mono"
                style={selectStyle}
              >
                {Array.from({ length: 28 }, (_, i) => i + 1).map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          )}

          {/* Add button */}
          <button
            onClick={handleAdd}
            disabled={saving || (cadence === "weekly" && selectedDays.length === 0)}
            className={clsx(
              "flex items-center gap-2 px-4 py-1.5 t-small border transition-colors",
              saving || (cadence === "weekly" && selectedDays.length === 0)
                ? "opacity-40 cursor-not-allowed"
                : "hover:opacity-90"
            )}
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
          >
            {saving && <Loader2 size={12} strokeWidth={2} className="animate-spin" />}
            Add Schedule
          </button>

          {/* Existing schedules */}
          {schedules.length > 0 && (
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                Active Schedules
              </p>
              <div className="border border-line" style={{ background: "var(--bg-0)" }}>
                {schedules.map((s, i) => (
                  <div
                    key={s.id}
                    className={clsx("flex items-center gap-3 px-3 py-2.5", i > 0 && "border-t border-line")}
                  >
                    {/* Enable toggle */}
                    <button
                      onClick={() => handleToggle(s)}
                      className="relative border transition-colors shrink-0"
                      style={{
                        width: 32, height: 18,
                        background: s.enabled ? "var(--accent)" : "var(--bg-2)",
                        borderColor: s.enabled ? "var(--accent)" : "var(--line)",
                      }}
                      title={s.enabled ? "Disable" : "Enable"}
                    >
                      <span style={{
                        position: "absolute", top: 2,
                        left: s.enabled ? 14 : 2,
                        width: 12, height: 12,
                        background: s.enabled ? "var(--bg-0)" : "var(--fg-3)",
                        transition: "left 0.15s",
                      }} />
                    </button>

                    <div className="flex-1 min-w-0">
                      <p className="t-small" style={{ color: s.enabled ? "var(--fg-0)" : "var(--fg-3)" }}>
                        {scheduleLabel(s)}
                      </p>
                      <p className="t-micro" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
                        {s.last_run_at ? `last: ${fmtTime(s.last_run_at)}` : "never run"}
                        {s.enabled && s.next_run_at ? ` · next: ${fmtNextRun(s.next_run_at)}` : ""}
                      </p>
                    </div>

                    <button
                      onClick={() => handleDelete(s.id)}
                      disabled={deletingId === s.id}
                      className="flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors shrink-0"
                      style={{ color: "var(--fg-3)" }}
                      title="Remove schedule"
                    >
                      {deletingId === s.id
                        ? <Loader2 size={11} strokeWidth={1.6} className="animate-spin" />
                        : <Trash2 size={11} strokeWidth={1.6} />}
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

interface CheckEditModalProps {
  check: CheckRow;
  onClose: () => void;
  onSave: (updated: CheckRow) => void;
}

function CheckEditModal({ check, onClose, onSave }: CheckEditModalProps) {
  const [dataset, setDataset] = useState(check.dataset);
  const [column, setColumn] = useState(check.column);
  const [detector, setDetector] = useState(check.check);
  const [warnThreshold, setWarnThreshold] = useState("0.05");
  const [failThreshold, setFailThreshold] = useState("0.10");
  const [baseline, setBaseline] = useState("14d");
  const [enabled, setEnabled] = useState(true);

  function handleSave() {
    onSave({ ...check, dataset, column, check: detector });
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.55)" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="border border-line" style={{ background: "var(--bg-1)", width: 480, maxHeight: "90vh", overflow: "auto" }}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="t-h3" style={{ color: "var(--fg-0)" }}>Edit Check</span>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-6 h-6 border border-line hover:bg-bg-2 transition-colors"
            style={{ color: "var(--fg-2)" }}
          >
            <X size={12} strokeWidth={1.6} />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <label className="block space-y-1">
            <span className="t-micro" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Detector</span>
            <input className="w-full px-3 py-1.5 border border-line t-small outline-none font-mono" style={{ background: "var(--bg-2)", color: "var(--fg-0)" }} value={detector} onChange={e => setDetector(e.target.value)} />
          </label>
          <label className="block space-y-1">
            <span className="t-micro" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Dataset</span>
            <input className="w-full px-3 py-1.5 border border-line t-small outline-none font-mono" style={{ background: "var(--bg-2)", color: "var(--fg-0)" }} value={dataset} onChange={e => setDataset(e.target.value)} />
          </label>
          <label className="block space-y-1">
            <span className="t-micro" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Column</span>
            <input className="w-full px-3 py-1.5 border border-line t-small outline-none font-mono" style={{ background: "var(--bg-2)", color: "var(--fg-0)" }} value={column} onChange={e => setColumn(e.target.value)} />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block space-y-1">
              <span className="t-micro" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Warn threshold</span>
              <input type="number" step="0.01" className="w-full px-3 py-1.5 border border-line t-small outline-none font-mono" style={{ background: "var(--bg-2)", color: "var(--warn)" }} value={warnThreshold} onChange={e => setWarnThreshold(e.target.value)} />
            </label>
            <label className="block space-y-1">
              <span className="t-micro" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Fail threshold</span>
              <input type="number" step="0.01" className="w-full px-3 py-1.5 border border-line t-small outline-none font-mono" style={{ background: "var(--bg-2)", color: "var(--fail)" }} value={failThreshold} onChange={e => setFailThreshold(e.target.value)} />
            </label>
          </div>
          <label className="block space-y-1">
            <span className="t-micro" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Baseline window</span>
            <input className="w-full px-3 py-1.5 border border-line t-small outline-none font-mono" style={{ background: "var(--bg-2)", color: "var(--fg-0)" }} placeholder="e.g. 14d" value={baseline} onChange={e => setBaseline(e.target.value)} />
          </label>
          <div className="flex items-center justify-between py-1">
            <span className="t-small" style={{ color: "var(--fg-1)" }}>Enabled</span>
            <button
              onClick={() => setEnabled(v => !v)}
              className="relative border border-line transition-colors"
              style={{ width: 36, height: 20, background: enabled ? "var(--accent)" : "var(--bg-2)", borderColor: enabled ? "var(--accent)" : "var(--line)" }}
              aria-label={enabled ? "Disable check" : "Enable check"}
            >
              <span style={{ position: "absolute", top: 2, left: enabled ? 18 : 2, width: 14, height: 14, background: enabled ? "var(--bg-0)" : "var(--fg-3)", transition: "left 0.15s" }} />
            </button>
          </div>
          <div>
            <p className="t-micro mb-1.5" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Preview</p>
            <pre className="t-micro font-mono p-2.5 overflow-x-auto" style={{ background: "var(--bg-0)", color: "var(--fg-1)", border: "1px solid var(--line)", lineHeight: 1.6 }}>
              {`check: ${detector}\ntable: ${dataset}\ncolumn: ${column}\nthreshold:\n  warn: ${warnThreshold}\n  fail: ${failThreshold}\nbaseline: ${baseline}\nenabled: ${enabled}`}
            </pre>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-line">
          <button onClick={onClose} className="px-3 py-1.5 t-small border border-line hover:bg-bg-2 transition-colors" style={{ color: "var(--fg-1)" }}>Cancel</button>
          <button onClick={handleSave} className="px-3 py-1.5 t-small border transition-colors hover:opacity-90" style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}>Save</button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Right panel
// ---------------------------------------------------------------------------

function RightPanel({ selectedCheckId, checks, onEditCheck }: {
  selectedCheckId: string | null;
  checks: CheckRow[];
  onEditCheck: (id: string) => void;
}) {
  const [prompt, setPrompt] = useState("");
  const [generatedYaml, setGeneratedYaml] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  function generate() {
    if (!prompt.trim()) return;
    setGenerating(true);
    setTimeout(() => {
      setGeneratedYaml(
        `check: custom_check\n# Generated from: "${prompt}"\ntable: <table>\ncolumn: <column>\nparams: {}`
      );
      setGenerating(false);
    }, 800);
  }

  if (selectedCheckId) {
    const chk = checks.find(c => c.id === selectedCheckId);
    if (!chk) return null;
    return (
      <div className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="t-h3" style={{ color: "var(--fg-0)" }}>{chk.check}</p>
            <p className="t-small font-mono mt-0.5" style={{ color: "var(--fg-1)" }}>{chk.dataset}.{chk.column}</p>
          </div>
          <button
            onClick={() => onEditCheck(chk.id)}
            className="px-2.5 py-1 t-micro border border-line hover:border-accent transition-colors flex-shrink-0"
            style={{ color: "var(--fg-1)" }}
          >
            Edit
          </button>
        </div>
        <YamlBlock
          code={`check: ${chk.check}\ntable: ${chk.dataset}\ncolumn: ${chk.column}\nthreshold:\n  warn: 0.05\n  fail: 0.10\nbaseline: 14d`}
        />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-5 overflow-y-auto h-full">
      <div className="flex items-center gap-2">
        <Sparkles size={13} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
        <span className="t-h3" style={{ color: "var(--fg-0)" }}>Author a Check</span>
      </div>
      <div className="space-y-3">
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Describe a check in plain English..."
          rows={3}
          className="w-full px-3 py-2 border border-line t-small outline-none resize-none"
          style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
        />
        <button
          onClick={generate}
          disabled={generating || !prompt.trim()}
          className={clsx(
            "px-3 py-1.5 t-small border transition-colors",
            generating || !prompt.trim() ? "opacity-40 cursor-not-allowed" : "hover:opacity-90"
          )}
          style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
        >
          {generating ? "Generating..." : "Generate"}
        </button>
        {generatedYaml && <YamlBlock code={generatedYaml} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ChecksPage() {
  const [activeCategory, setActiveCategory] = useState<CategoryLabel>("All");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingCheckId, setEditingCheckId] = useState<string | null>(null);
  const [checks, setChecks] = useState<CheckRow[]>([]);
  const [loading, setLoading] = useState(true);

  // Schedule state
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [lastRunAt, setLastRunAt] = useState<string | null>(null);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [running, setRunning] = useState(false);

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
      .then((data: unknown[]) => {
        setChecks((data as Parameters<typeof apiToRow>[0][]).map(apiToRow));
      })
      .catch(() => setChecks([]))
      .finally(() => setLoading(false));

    loadSchedules();
  }, [loadSchedules]);

  async function handleRunNow() {
    setRunning(true);
    try {
      await fetch("/api/v1/checks/refresh", { method: "POST" });
      // Brief delay then reload schedule status to pick up new last_run_at
      setTimeout(() => {
        loadSchedules();
        setRunning(false);
      }, 1500);
    } catch {
      setRunning(false);
    }
  }

  const cat = CATEGORIES.find(c => c.label === activeCategory)!;
  const visibleChecks = cat.group === null ? checks : checks.filter(c => c.group === cat.group);
  const editingCheck = editingCheckId ? checks.find(c => c.id === editingCheckId) ?? null : null;

  // Next schedule summary for the header
  const nextSchedule = schedules
    .filter(s => s.enabled && s.next_run_at)
    .sort((a, b) => new Date(a.next_run_at!).getTime() - new Date(b.next_run_at!).getTime())[0] ?? null;

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 44px)", overflow: "hidden" }}>
      {/* Modals */}
      {editingCheck && (
        <CheckEditModal
          check={editingCheck}
          onClose={() => setEditingCheckId(null)}
          onSave={updated => setChecks(prev => prev.map(c => c.id === updated.id ? updated : c))}
        />
      )}
      {scheduleOpen && (
        <ScheduleModal
          schedules={schedules}
          onClose={() => setScheduleOpen(false)}
          onCreated={s => setSchedules(prev => [...prev, s])}
          onDeleted={id => setSchedules(prev => prev.filter(s => s.id !== id))}
          onToggled={updated => setSchedules(prev => prev.map(s => s.id === updated.id ? updated : s))}
        />
      )}

      {/* Top action bar */}
      <div
        className="flex items-center justify-between px-4 py-2 border-b border-line shrink-0"
        style={{ background: "var(--bg-1)" }}
      >
        <div className="flex items-center gap-4">
          <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Checks</span>
          {lastRunAt && (
            <span className="t-micro" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
              Last run: {fmtTime(lastRunAt)}
            </span>
          )}
          {nextSchedule && (
            <span className="t-micro" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
              · Next: {fmtNextRun(nextSchedule.next_run_at)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRunNow}
            disabled={running}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
            style={{ background: "var(--bg-2)", color: "var(--fg-0)", borderColor: "var(--line)" }}
          >
            {running
              ? <Loader2 size={12} strokeWidth={1.6} className="animate-spin" />
              : <Play size={12} strokeWidth={1.6} />}
            {running ? "Starting..." : "Run Now"}
          </button>
          <button
            onClick={() => setScheduleOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80"
            style={{
              background: schedules.some(s => s.enabled) ? "var(--accent-bg)" : "var(--bg-2)",
              color: schedules.some(s => s.enabled) ? "var(--accent)" : "var(--fg-1)",
              borderColor: schedules.some(s => s.enabled) ? "var(--accent)" : "var(--line)",
            }}
          >
            <CalendarClock size={12} strokeWidth={1.6} />
            {schedules.some(s => s.enabled) ? `Scheduled (${schedules.filter(s => s.enabled).length})` : "Schedule"}
          </button>
        </div>
      </div>

      {/* 3-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: category nav */}
        <div className="flex-shrink-0 border-r border-line overflow-y-auto" style={{ width: 200, background: "var(--bg-1)" }}>
          <div className="px-3 py-2 t-micro border-b border-line" style={{ color: "var(--fg-3)", letterSpacing: "0.10em", textTransform: "uppercase" }}>
            Category
          </div>
          {CATEGORIES.map(cat => {
            const active = activeCategory === cat.label;
            const groupChecks = cat.group === null ? checks : checks.filter(c => c.group === cat.group);
            const passCount = groupChecks.filter(c => c.verdict === "pass").length;
            const warnCount = groupChecks.filter(c => c.verdict === "warn").length;
            const failCount = groupChecks.filter(c => c.verdict === "fail").length;
            return (
              <button
                key={cat.label}
                onClick={() => { setActiveCategory(cat.label); setSelectedId(null); }}
                className={clsx(
                  "w-full px-3 py-2 text-left transition-colors border-l-2",
                  active ? "border-accent" : "border-transparent hover:bg-bg-2"
                )}
                style={{ background: active ? "var(--bg-2)" : "transparent" }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="t-small" style={{ color: active ? "var(--fg-0)" : "var(--fg-1)" }}>{cat.label}</span>
                  {groupChecks.length > 0 && (
                    <span className="flex items-center gap-1.5 flex-shrink-0">
                      <span className="flex items-center gap-0.5">
                        <span style={{ display: "inline-block", width: 5, height: 5, background: "var(--pass)", flexShrink: 0 }} />
                        <span className="t-micro font-mono" style={{ color: "var(--pass)" }}>{passCount}</span>
                      </span>
                      {warnCount > 0 && (
                        <span className="flex items-center gap-0.5">
                          <span style={{ display: "inline-block", width: 5, height: 5, background: "var(--warn)", flexShrink: 0 }} />
                          <span className="t-micro font-mono" style={{ color: "var(--warn)" }}>{warnCount}</span>
                        </span>
                      )}
                      {failCount > 0 && (
                        <span className="flex items-center gap-0.5">
                          <span style={{ display: "inline-block", width: 5, height: 5, background: "var(--fail)", flexShrink: 0 }} />
                          <span className="t-micro font-mono" style={{ color: "var(--fail)" }}>{failCount}</span>
                        </span>
                      )}
                    </span>
                  )}
                </div>
                <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)", lineHeight: 1.3 }}>{cat.hint}</p>
              </button>
            );
          })}
        </div>

        {/* Center: check list */}
        <div className="flex flex-col flex-1 border-r border-line overflow-hidden">
          <div className="px-3 py-2 border-b border-line t-micro flex items-center justify-between" style={{ background: "var(--bg-1)", flexShrink: 0 }}>
            <span style={{ color: "var(--fg-3)", letterSpacing: "0.10em", textTransform: "uppercase" }}>{activeCategory}</span>
            <span className="font-mono" style={{ color: "var(--fg-3)" }}>
              {visibleChecks.length} check{visibleChecks.length !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="px-4 py-8 t-small text-center" style={{ color: "var(--fg-3)" }}>Loading checks...</div>
            ) : visibleChecks.length === 0 ? (
              <div className="px-4 py-8 t-small text-center" style={{ color: "var(--fg-2)" }}>
                {checks.length === 0
                  ? "No checks yet. Add a source to get started."
                  : "No checks in this category."}
              </div>
            ) : (
              <table className="w-full" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr className="border-b border-line" style={{ background: "var(--bg-1)" }}>
                    {["", "Dataset.Column", "Check", "Score", ""].map((h, i) => (
                      <th key={i} className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visibleChecks.map(chk => {
                    const selected = selectedId === chk.id;
                    return (
                      <tr
                        key={chk.id}
                        onClick={() => setSelectedId(selected ? null : chk.id)}
                        className="border-b border-line last:border-0 cursor-pointer transition-colors"
                        style={{ background: selected ? "var(--bg-2)" : undefined }}
                        onMouseEnter={e => { if (!selected) (e.currentTarget as HTMLTableRowElement).style.background = "var(--bg-2)"; }}
                        onMouseLeave={e => { if (!selected) (e.currentTarget as HTMLTableRowElement).style.background = ""; }}
                      >
                        <td className="px-3 py-2 w-8"><StatusDot verdict={chk.verdict} /></td>
                        <td className="px-3 py-2">
                          <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{chk.dataset}.{chk.column}</span>
                        </td>
                        <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>{chk.check}</td>
                        <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>{chk.score}</td>
                        <td className="px-3 py-2 w-12 text-right">
                          <button
                            onClick={e => { e.stopPropagation(); setEditingCheckId(chk.id); }}
                            className="t-micro px-2 py-0.5 border border-line hover:border-accent transition-colors"
                            style={{ color: "var(--fg-2)" }}
                          >
                            Edit
                          </button>
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
        <div className="overflow-y-auto flex-shrink-0" style={{ width: 400, background: "var(--bg-1)" }}>
          <RightPanel selectedCheckId={selectedId} checks={checks} onEditCheck={setEditingCheckId} />
        </div>
      </div>
    </div>
  );
}

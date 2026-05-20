"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, Loader2, ChevronLeft, X, Sparkles, TrendingUp, RefreshCw } from "lucide-react";
import { clsx } from "clsx";

// ---------------------------------------------------------------------------
// Field definitions
// ---------------------------------------------------------------------------

type FieldDef = {
  key: string;
  label: string;
  type: "text" | "password" | "textarea" | "toggle";
  placeholder: string;
  help?: string;
};

const ENGINE_FIELDS: Record<string, FieldDef[]> = {
  postgres: [
    { key: "host", label: "Host", type: "text", placeholder: "db.example.com" },
    { key: "port", label: "Port", type: "text", placeholder: "5432" },
    { key: "database", label: "Database", type: "text", placeholder: "production" },
    { key: "username", label: "Username", type: "text", placeholder: "dqt_readonly", help: "Use a read-only role — dqt never writes to your warehouse." },
    { key: "password", label: "Password", type: "password", placeholder: "" },
  ],
  mysql: [
    { key: "host", label: "Host", type: "text", placeholder: "db.example.com" },
    { key: "port", label: "Port", type: "text", placeholder: "3306" },
    { key: "database", label: "Database", type: "text", placeholder: "production" },
    { key: "username", label: "Username", type: "text", placeholder: "dqt_readonly", help: "Use a read-only role — dqt never writes to your warehouse." },
    { key: "password", label: "Password", type: "password", placeholder: "" },
  ],
  clickhouse: [
    { key: "url", label: "URL", type: "text", placeholder: "clickhouse.example.com" },
    { key: "port", label: "Port", type: "text", placeholder: "8443" },
    { key: "secure", label: "Secure (TLS)", type: "toggle", placeholder: "" },
    { key: "username", label: "User", type: "text", placeholder: "dqt_readonly" },
    { key: "password", label: "Password", type: "password", placeholder: "" },
  ],
  bigquery: [
    {
      key: "service_account_json",
      label: "Service Account Key",
      type: "textarea",
      placeholder: "Paste JSON key here",
      help: "Upload or paste your GCP service account key file (.json). The project ID is read from the key automatically.",
    },
    { key: "project", label: "GCP Project ID", type: "text", placeholder: "auto-detected from key" },
    {
      key: "dataset",
      label: "Dataset",
      type: "text",
      placeholder: "analytics",
      help: "Leave blank to scan all datasets in the project.",
    },
  ],
  snowflake: [
    { key: "account", label: "Account", type: "text", placeholder: "myaccount.us-east-1" },
    { key: "database", label: "Database", type: "text", placeholder: "PRODUCTION" },
    { key: "warehouse", label: "Warehouse", type: "text", placeholder: "DQT_WH" },
    { key: "username", label: "Username", type: "text", placeholder: "DQT_READONLY", help: "Use a read-only role — dqt never writes to your warehouse." },
    { key: "password", label: "Password", type: "password", placeholder: "" },
  ],
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type Step = 1 | 2 | 3 | 4 | 5;
type CheckTier = "essential" | "recommended" | "full_coverage";

const HEALTH_STEP_LABELS = ["TCP Reach", "Authentication", "Info Schema Read", "Sample SELECT", "Latency Probe", "Clock Skew"];

const HEALTH_CHECK_BULLETS = [
  "TCP connectivity",
  "Authentication",
  "Schema inspection",
  "Sample SELECT",
  "Latency probe",
  "Clock alignment",
];

const ENGINE_HINTS: Record<string, string> = {
  bigquery:   "Service Account JSON: paste or drop a GCP key file. ADC: uses gcloud/GOOGLE_APPLICATION_CREDENTIALS on the server. Key File Path: absolute path to a JSON key on the server.",
  postgres:   "Need a read-only user? CREATE USER dqt_readonly WITH PASSWORD '...' then GRANT SELECT ON ALL TABLES.",
  mysql:      "Need a read-only user? GRANT SELECT ON *.* TO 'dqt_readonly'@'%' IDENTIFIED BY '...'",
  clickhouse: "Need a read-only user? CREATE USER dqt_readonly IDENTIFIED BY '...' SETTINGS readonly = 1.",
  snowflake:  "Need a read-only role? CREATE ROLE dqt_role; GRANT SELECT ON ALL TABLES IN DATABASE ... TO ROLE dqt_role.",
};

const WIZARD_STEPS: { id: Step; label: string }[] = [
  { id: 1, label: "Configure" },
  { id: 2, label: "Test & Verify" },
  { id: 3, label: "Choose Datasets" },
  { id: 4, label: "Review Checks" },
  { id: 5, label: "Add Metrics" },
];

const TIER_LABELS: Record<CheckTier, string> = {
  essential: "Essential",
  recommended: "Recommended",
  full_coverage: "Full coverage",
};
const TIER_DESC: Record<CheckTier, string> = {
  essential: "Core data integrity checks (nulls, PK uniqueness, format validation)",
  recommended: "Adds statistical monitoring and drift detection",
  full_coverage: "All available checks for maximum observability",
};

const ENGINE_DISPLAY_NAMES: Record<string, string> = {
  postgres: "PostgreSQL",
  mysql: "MySQL",
  clickhouse: "ClickHouse",
  bigquery: "BigQuery",
  snowflake: "Snowflake",
};

const SENSITIVE_FIELDS = new Set(["password", "service_account_json"]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function tierIncludes(activeTier: CheckTier, itemTier: CheckTier): boolean {
  const order: CheckTier[] = ["essential", "recommended", "full_coverage"];
  return order.indexOf(itemTier) <= order.indexOf(activeTier);
}

function getConnectionPreview(engine: string, values: Record<string, string>): string {
  switch (engine.toLowerCase()) {
    case "bigquery": {
      const proj = values.project || "project";
      const ds = values.dataset || "*";
      return `bigquery://${proj}?dataset=${ds}`;
    }
    case "postgres": {
      const user = values.username ? `${values.username}@` : "";
      const host = values.host || "host";
      const port = values.port || "5432";
      const db = values.database || "db";
      return `postgresql://${user}${host}:${port}/${db}`;
    }
    case "mysql": {
      const user = values.username ? `${values.username}@` : "";
      const host = values.host || "host";
      const port = values.port || "3306";
      const db = values.database || "db";
      return `mysql://${user}${host}:${port}/${db}`;
    }
    case "clickhouse": {
      const host = values.url || values.host || "host";
      const port = values.port || "8443";
      const scheme = values.secure === "true" ? "clickhouses" : "clickhouse";
      return `${scheme}://${host}:${port}/default`;
    }
    case "snowflake": {
      const account = values.account || "account";
      const db = values.database || "DB";
      const wh = values.warehouse ? `?warehouse=${values.warehouse}` : "";
      return `snowflake://${account}/${db}${wh}`;
    }
    default:
      return `${engine}://…`;
  }
}

// ---------------------------------------------------------------------------
// JsonDropZone — file drop + textarea for service account JSON
// ---------------------------------------------------------------------------

function JsonDropZone({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [dragging, setDragging] = useState(false);
  const [focused, setFocused] = useState(false);
  const hasContent = value.trim().length > 0;

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (text) onChange(text);
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className="border border-dashed flex items-center justify-center py-4 transition-colors"
        style={{
          borderColor: dragging ? "var(--accent)" : hasContent ? "var(--pass)" : "var(--line)",
          background: dragging ? "var(--accent-bg)" : hasContent ? "rgba(127,179,148,0.06)" : "var(--bg-1)",
        }}
      >
        {hasContent ? (
          <span className="t-small flex items-center gap-2" style={{ color: "var(--pass)" }}>
            <Check size={13} strokeWidth={2.5} />
            JSON loaded
          </span>
        ) : (
          <span className="t-small" style={{ color: dragging ? "var(--accent)" : "var(--fg-3)" }}>
            {dragging ? "Release to load" : "Drop key.json here"}
          </span>
        )}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        rows={focused || hasContent ? 7 : 4}
        placeholder="...or paste JSON below"
        className="w-full px-4 py-3 border t-small font-mono outline-none resize-y"
        style={{
          background: "var(--bg-1)",
          color: "var(--fg-0)",
          borderColor: focused ? "var(--accent)" : "var(--line)",
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HealthStep {
  name: string;
  display: string;
  status: "pass" | "fail" | "skip";
  latency_ms: number;
  detail: string;
}

interface TableItem { name: string; schema: string; watched: boolean }

interface CheckSuggestion {
  table: string;
  column: string;
  detector_slug: string;
  params: Record<string, unknown>;
  rationale: string;
  confidence: number;
  tier: CheckTier;
}

interface WizardProps {
  engine: string;
  sourceId?: string;
  initialValues?: Record<string, string>;
  mode?: "create" | "edit";
}

// ---------------------------------------------------------------------------
// Wizard
// ---------------------------------------------------------------------------

export function Wizard({ engine, sourceId, initialValues = {}, mode = "create" }: WizardProps) {
  const router = useRouter();
  const sessionKey = `wizard-draft-${engine}`;

  const [step, setStep] = useState<Step>(1);
  const [connectionName, setConnectionName] = useState(initialValues.name ?? "");
  const [activeSourceId, setActiveSourceId] = useState<string | undefined>(sourceId);
  const [activeField, setActiveField] = useState<string | null>(null);
  const [draftSaved, setDraftSaved] = useState(false);

  const fields = ENGINE_FIELDS[engine] ?? ENGINE_FIELDS["postgres"];
  const [formValues, setFormValues] = useState<Record<string, string>>(() => {
    const defaults: Record<string, string> = {};
    for (const f of fields) defaults[f.key] = initialValues[f.key] ?? "";
    return defaults;
  });

  // Restore draft from sessionStorage on mount
  useEffect(() => {
    if (Object.keys(initialValues).length > 0) return;
    const saved = sessionStorage.getItem(sessionKey);
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved) as Record<string, string>;
      setFormValues((prev) => {
        const next = { ...prev };
        for (const [k, v] of Object.entries(parsed)) {
          if (k !== "__name" && typeof v === "string" && !SENSITIVE_FIELDS.has(k)) {
            next[k] = v;
          }
        }
        return next;
      });
      if (parsed.__name) setConnectionName(parsed.__name);
    } catch { /* ignore */ }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Save draft on change (non-sensitive fields only)
  useEffect(() => {
    if (step !== 1) return;
    const toSave: Record<string, string> = { __name: connectionName };
    for (const [k, v] of Object.entries(formValues)) {
      if (!SENSITIVE_FIELDS.has(k)) toSave[k] = v;
    }
    sessionStorage.setItem(sessionKey, JSON.stringify(toSave));
    setDraftSaved(true);
    const t = setTimeout(() => setDraftSaved(false), 2000);
    return () => clearTimeout(t);
  }, [formValues, connectionName, step, sessionKey]);

  // Step 2 state
  const [healthSteps, setHealthSteps] = useState<HealthStep[]>([]);
  const [healthPassed, setHealthPassed] = useState(false);
  const [healthDone, setHealthDone] = useState(false);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Step 3 state
  const [tables, setTables] = useState<TableItem[]>([]);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set());

  // Step 4 state
  const [suggestions, setSuggestions] = useState<CheckSuggestion[]>([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [activeTier, setActiveTier] = useState<CheckTier>("essential");
  const [selectedChecks, setSelectedChecks] = useState<Set<string>>(new Set());
  const [savingChecks, setSavingChecks] = useState(false);

  // Step 5 state
  const [selectedMetrics, setSelectedMetrics] = useState<Set<string>>(new Set());
  const [savingMetrics, setSavingMetrics] = useState(false);


  const runHealthCheck = useCallback(async () => {
    setHealthSteps([]);
    setHealthDone(false);
    setHealthPassed(false);
    setHealthLoading(true);
    setHealthError(null);

    try {
      const isBQ = engine === "bigquery";
      const host = isBQ
        ? (formValues.project || "")
        : (formValues.url || formValues.host || formValues.account || "");
      const port = isBQ ? 0 : parseInt(formValues.port || "8443", 10);
      const dbName = isBQ
        ? (formValues.dataset || "")
        : (formValues.database || formValues.project || "default");
      const password = isBQ ? (formValues.service_account_json || "") : (formValues.password || "");

      const res = await fetch("/api/v1/sources/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engine,
          host,
          port: isNaN(port) ? 0 : port,
          username: formValues.username || "",
          password,
          secure: formValues.secure === "true",
          db_name: dbName,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setHealthError(data.detail || "Connection test failed");
        setHealthDone(true);
        setHealthLoading(false);
        return;
      }

      for (const s of (data.steps as HealthStep[])) {
        await new Promise<void>((r) => setTimeout(r, 200));
        setHealthSteps((prev) => [...prev, s]);
      }
      setHealthPassed(data.passed);
    } catch {
      setHealthError("Network error -- could not reach server");
    } finally {
      setHealthDone(true);
      setHealthLoading(false);
    }
  }, [engine, formValues]);

  useEffect(() => {
    if (step === 2) runHealthCheck();
  }, [step, runHealthCheck]);

  function canProceedFromHealth(): boolean {
    if (!healthDone) return false;
    if (healthPassed) return true;
    const byName = Object.fromEntries(healthSteps.map((s) => [s.name, s]));
    return (
      byName["tcp_reach"]?.status === "pass" &&
      byName["info_schema"]?.status === "pass" &&
      byName["sample_select"]?.status === "pass"
    );
  }

  async function handleAdvanceToStep3() {
    if (mode === "create" && !activeSourceId) {
      const isBQ = engine === "bigquery";
      const host = isBQ
        ? (formValues.project || "")
        : (formValues.url || formValues.host || formValues.account || "");
      const port = isBQ ? 0 : parseInt(formValues.port || "8443", 10);
      const dbName = isBQ
        ? (formValues.dataset || "")
        : (formValues.database || formValues.project || "default");
      const password = isBQ ? (formValues.service_account_json || "") : (formValues.password || "");
      const name = connectionName.trim() || (isBQ ? `bigquery://${host}` : `${engine}://${host}`);

      try {
        const res = await fetch("/api/v1/sources", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            engine,
            host,
            port: isNaN(port) ? 0 : port,
            username: formValues.username || "",
            password,
            secure: formValues.secure === "true",
            db_name: dbName,
          }),
        });
        if (res.ok) {
          const created = await res.json();
          setActiveSourceId(created.id);
        }
      } catch {
        // proceed; table fetch will fail gracefully
      }
    }
    sessionStorage.removeItem(sessionKey);
    setStep(3);
  }

  useEffect(() => {
    if (step !== 3 || !activeSourceId) return;
    setTablesLoading(true);
    fetch(`/api/v1/sources/${encodeURIComponent(activeSourceId)}/tables`)
      .then((r) => r.ok ? r.json() : [])
      .then((data: TableItem[]) => {
        setTables(data);
        setSelectedTables(new Set(data.filter((t) => t.watched).map((t) => t.name)));
      })
      .catch(() => setTables([]))
      .finally(() => setTablesLoading(false));
  }, [step, activeSourceId]);

  async function handleAdvanceToStep4() {
    if (!activeSourceId) { setStep(4); return; }

    await fetch(`/api/v1/sources/${encodeURIComponent(activeSourceId)}/tables`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tables: Array.from(selectedTables) }),
    }).catch(() => null);

    setSuggestLoading(true);
    setStep(4);
    setSuggestions([]);

    try {
      const res = await fetch(
        `/api/v1/sources/${encodeURIComponent(activeSourceId)}/suggest-checks`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tables: Array.from(selectedTables) }),
        }
      );
      if (res.ok) {
        const data: CheckSuggestion[] = await res.json();
        setSuggestions(data);
        const keys = new Set(
          data
            .filter((s) => s.tier === "essential")
            .map((s) => `${s.table}.${s.column}.${s.detector_slug}`)
        );
        setSelectedChecks(keys);
      }
    } catch {
      // suggestions optional
    } finally {
      setSuggestLoading(false);
    }
  }

  function handleTierChange(tier: CheckTier) {
    setActiveTier(tier);
    const keys = new Set(
      suggestions
        .filter((s) => tierIncludes(tier, s.tier))
        .map((s) => `${s.table}.${s.column}.${s.detector_slug}`)
    );
    setSelectedChecks(keys);
  }

  function toggleCheck(key: string) {
    setSelectedChecks((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function checkedColumns(): Array<{ table: string; column: string; checkCount: number }> {
    const map = new Map<string, number>();
    selectedChecks.forEach((key) => {
      const parts = key.split(".");
      if (parts.length < 3) return;
      const colKey = `${parts[0]}.${parts[1]}`;
      map.set(colKey, (map.get(colKey) ?? 0) + 1);
    });
    return Array.from(map.entries()).map(([k, count]) => {
      const dot = k.indexOf(".");
      return { table: k.slice(0, dot), column: k.slice(dot + 1), checkCount: count };
    });
  }

  async function handleAdvanceToStep5() {
    if (!activeSourceId) { router.push("/sources"); return; }
    setSavingChecks(true);
    try {
      if (selectedChecks.size > 0) {
        const checksToSave = suggestions
          .filter((s) => selectedChecks.has(`${s.table}.${s.column}.${s.detector_slug}`))
          .map((s) => ({
            dataset_id: s.table,
            column_name: s.column,
            detector_slug: s.detector_slug,
            params: s.params,
            rationale: s.rationale,
          }));
        await fetch("/api/v1/column-checks/batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ checks: checksToSave }),
        }).catch(() => null);
      }

      const cols = checkedColumns();
      if (cols.length === 0) {
        router.push(`/sources/${activeSourceId}`);
        return;
      }
      setSelectedMetrics(new Set(cols.map((c) => `${c.table}.${c.column}`)));
      setStep(5);
    } finally {
      setSavingChecks(false);
    }
  }

  async function handleFinish() {
    if (!activeSourceId) { router.push("/sources"); return; }
    setSavingMetrics(true);
    try {
      if (selectedMetrics.size > 0) {
        const metricsToSave = checkedColumns()
          .filter((c) => selectedMetrics.has(`${c.table}.${c.column}`))
          .map((c) => ({
            display_name: `${c.table}.${c.column}`,
            kind: "count",
            dataset: c.table,
            description: `Auto-created from data quality checks on ${c.table}.${c.column}`,
          }));
        await fetch("/api/v1/metrics/batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ metrics: metricsToSave }),
        }).catch(() => null);
      }
      router.push(`/sources/${activeSourceId}`);
    } finally {
      setSavingMetrics(false);
    }
  }

  function toggleTable(t: string) {
    setSelectedTables((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }

  function toggleMetric(key: string) {
    setSelectedMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function setField(key: string, value: string) {
    setFormValues((prev) => {
      const next = { ...prev, [key]: value };
      if (key === "service_account_json" && engine === "bigquery" && !prev.project) {
        try {
          const info = JSON.parse(value);
          const proj = info.quota_project_id || info.project_id;
          if (proj) next.project = proj;
        } catch { /* ignore */ }
      }
      return next;
    });
  }

  // Connection summary for step 2 panel
  const connSummary = [
    ["engine", engine],
    ["host", formValues.url || formValues.host || formValues.account || formValues.project || ""],
    ["port", formValues.port || ""],
    ["database", formValues.database || formValues.dataset || ""],
    ["user", formValues.username || ""],
  ].filter(([, v]) => v) as [string, string][];

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex gap-10">
      {/* Vertical stepper */}
      <div style={{ width: 148, flexShrink: 0, paddingTop: 2 }}>
        {WIZARD_STEPS.map((s, idx) => {
          const active = step === s.id;
          const done = step > s.id;
          return (
            <div key={s.id} className="flex gap-3">
              <div className="flex flex-col items-center" style={{ width: 20 }}>
                {/* Circle: only for active and done; bare number for upcoming */}
                {done ? (
                  <div
                    className="flex items-center justify-center flex-shrink-0"
                    style={{ width: 20, height: 20, background: "var(--accent)", border: "1px solid var(--accent)" }}
                  >
                    <Check size={10} strokeWidth={2.5} style={{ color: "var(--bg-0)" }} />
                  </div>
                ) : active ? (
                  <div
                    className="flex items-center justify-center flex-shrink-0"
                    style={{ width: 20, height: 20, background: "var(--accent-bg)", border: "1px solid var(--accent)" }}
                  >
                    <div style={{ width: 5, height: 5, background: "var(--accent)", borderRadius: "50%" }} />
                  </div>
                ) : (
                  <div
                    className="flex items-center justify-center flex-shrink-0"
                    style={{ width: 20, height: 20 }}
                  >
                    <span style={{ fontSize: 11, color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)", lineHeight: 1 }}>
                      {s.id}
                    </span>
                  </div>
                )}
                {idx < WIZARD_STEPS.length - 1 && (
                  <div style={{ width: 1, height: 36, background: done ? "var(--accent)" : "var(--line)", opacity: done ? 0.3 : 1 }} />
                )}
              </div>
              <div style={{ paddingTop: 2 }}>
                <span
                  style={{
                    fontSize: 12,
                    color: active ? "var(--fg-0)" : done ? "var(--fg-2)" : "var(--fg-3)",
                    fontWeight: active ? 500 : 400,
                    fontFamily: "var(--font-jetbrains-mono)",
                    lineHeight: 1.4,
                  }}
                >
                  {s.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Content area */}
      <div className="flex-1 min-w-0">

        {/* ---- Step 1: Configure ---- */}
        {step === 1 && (
          <div
            className="grid gap-6"
            style={{ gridTemplateColumns: "1fr 200px" }}
          >
            {/* Left: form */}
            <div className="space-y-5">
              <div>
                <label className="block t-small mb-1.5 font-medium" style={{ color: "var(--fg-1)" }}>
                  Connection name
                </label>
                <input
                  type="text"
                  value={connectionName}
                  onChange={(e) => setConnectionName(e.target.value)}
                  onFocus={() => setActiveField("__name")}
                  onBlur={() => setActiveField(null)}
                  placeholder={`My ${ENGINE_DISPLAY_NAMES[engine] ?? engine} connection`}
                  className="w-full px-4 py-3 border t-body outline-none transition-colors"
                  style={{
                    background: "var(--bg-1)",
                    color: "var(--fg-0)",
                    borderColor: activeField === "__name" ? "var(--accent)" : "var(--line)",
                  }}
                />
              </div>

              {fields.map((f) => (
                <div key={f.key}>
                  <label className="block t-small mb-1.5 font-medium" style={{ color: "var(--fg-1)" }}>
                    {f.label}
                  </label>

                  {f.type === "textarea" && f.key === "service_account_json" ? (
                    <JsonDropZone
                      value={formValues[f.key] ?? ""}
                      onChange={(v) => setField(f.key, v)}
                    />
                  ) : f.type === "textarea" ? (
                    <textarea
                      value={formValues[f.key] ?? ""}
                      onChange={(e) => setField(f.key, e.target.value)}
                      onFocus={() => setActiveField(f.key)}
                      onBlur={() => setActiveField(null)}
                      placeholder={f.placeholder}
                      rows={4}
                      className="w-full px-4 py-3 border t-small font-mono outline-none resize-y"
                      style={{
                        background: "var(--bg-1)",
                        color: "var(--fg-0)",
                        borderColor: activeField === f.key ? "var(--accent)" : "var(--line)",
                        minHeight: 80,
                      }}
                    />
                  ) : f.type === "toggle" ? (
                    <button
                      type="button"
                      onClick={() => setField(f.key, formValues[f.key] === "true" ? "false" : "true")}
                      className="flex items-center gap-2 px-4 py-2.5 border t-small font-medium transition-colors"
                      style={{
                        borderColor: formValues[f.key] === "true" ? "var(--accent)" : "var(--line)",
                        background: formValues[f.key] === "true" ? "var(--accent-bg)" : "var(--bg-1)",
                        color: formValues[f.key] === "true" ? "var(--accent)" : "var(--fg-2)",
                        minWidth: 96,
                      }}
                    >
                      {formValues[f.key] === "true" ? "Enabled" : "Disabled"}
                    </button>
                  ) : (
                    <input
                      type={f.type}
                      value={formValues[f.key] ?? ""}
                      onChange={(e) => setField(f.key, e.target.value)}
                      onFocus={() => setActiveField(f.key)}
                      onBlur={() => setActiveField(null)}
                      placeholder={f.placeholder}
                      className="w-full px-4 py-3 border t-body outline-none transition-colors"
                      style={{
                        background: "var(--bg-1)",
                        color: "var(--fg-0)",
                        borderColor: activeField === f.key ? "var(--accent)" : "var(--line)",
                      }}
                    />
                  )}

                  {f.help && (
                    <p className="t-micro mt-1.5" style={{ color: "var(--fg-3)", lineHeight: 1.5 }}>
                      {f.help}
                    </p>
                  )}
                </div>
              ))}

              <div className="pt-2 flex items-center gap-3">
                <button
                  onClick={() => setStep(2)}
                  className="flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors hover:opacity-90"
                  style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
                >
                  Test Connection
                </button>
                <Link
                  href="/sources"
                  className="t-small transition-colors hover:opacity-60"
                  style={{ color: "var(--fg-3)" }}
                >
                  Cancel
                </Link>
                {draftSaved && (
                  <span className="t-micro" style={{ color: "var(--fg-3)" }}>draft saved</span>
                )}
              </div>
            </div>

            {/* Right: live preview + what happens next + hint */}
            <div className="space-y-4">
              <div className="border border-line p-4 space-y-3" style={{ background: "var(--bg-1)" }}>
                <p className="t-micro font-medium uppercase" style={{ color: "var(--fg-3)", letterSpacing: "0.1em" }}>
                  preview
                </p>
                <p
                  className="t-small font-mono break-all"
                  style={{ color: "var(--accent)", lineHeight: 1.6 }}
                >
                  {getConnectionPreview(engine, formValues)}
                </p>
              </div>

              <div className="border border-line p-4 space-y-3" style={{ background: "var(--bg-1)" }}>
                <p className="t-micro font-medium uppercase" style={{ color: "var(--fg-3)", letterSpacing: "0.1em" }}>
                  what happens next
                </p>
                <div className="space-y-1.5">
                  {HEALTH_CHECK_BULLETS.map((item, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div style={{ width: 4, height: 4, borderRadius: "50%", background: "var(--fg-3)", flexShrink: 0 }} />
                      <span className="t-micro" style={{ color: "var(--fg-2)" }}>{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              {ENGINE_HINTS[engine] && (
                <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
                  <p className="t-micro" style={{ color: "var(--fg-3)", lineHeight: 1.6 }}>
                    {ENGINE_HINTS[engine]}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ---- Step 2: Test & Verify ---- */}
        {step === 2 && (
          <div className="space-y-5">
            <div className="flex gap-5">
              {/* Health check table */}
              <div className="flex-1 border border-line" style={{ background: "var(--bg-1)" }}>
                {HEALTH_STEP_LABELS.map((label, i) => {
                  const stepResult = healthSteps[i];
                  const isActive = !healthDone && healthSteps.length === i && healthLoading;
                  const done = !!stepResult;
                  const failed = done && stepResult.status === "fail";
                  const statusColor = failed
                    ? "var(--fail)"
                    : stepResult?.status === "skip"
                    ? "var(--fg-3)"
                    : "var(--pass)";
                  return (
                    <div key={label}>
                      <div
                        className="flex items-center gap-3 px-4 py-3"
                        style={{ borderBottom: "1px solid var(--line)" }}
                      >
                        <div
                          className="flex items-center justify-center border flex-shrink-0"
                          style={{
                            width: 20,
                            height: 20,
                            borderColor: done ? statusColor : isActive ? "var(--accent)" : "var(--line)",
                            background: done ? statusColor : isActive ? "var(--accent-bg)" : "transparent",
                          }}
                        >
                          {done ? (
                            failed ? (
                              <X size={10} strokeWidth={2.5} style={{ color: "var(--bg-0)" }} />
                            ) : stepResult.status === "skip" ? (
                              <span style={{ color: "var(--bg-0)", fontSize: 9, fontWeight: 700, lineHeight: 1 }}>–</span>
                            ) : (
                              <Check size={10} strokeWidth={2.5} style={{ color: "var(--bg-0)" }} />
                            )
                          ) : isActive ? (
                            <Loader2 size={11} strokeWidth={2} className="animate-spin" style={{ color: "var(--accent)" }} />
                          ) : null}
                        </div>
                        <span
                          className="t-small flex-1"
                          style={{ color: done ? "var(--fg-0)" : isActive ? "var(--fg-0)" : "var(--fg-3)" }}
                        >
                          {label}
                        </span>
                        <span
                          className="t-micro font-mono"
                          style={{ width: 72, textAlign: "right", color: "var(--fg-3)", fontFeatureSettings: '"tnum"', flexShrink: 0 }}
                        >
                          {done && stepResult.status !== "fail" && stepResult.latency_ms > 0
                            ? `${stepResult.latency_ms.toFixed(0)}ms`
                            : ""}
                        </span>
                      </div>
                      {failed && stepResult.detail && (
                        <div
                          className="px-4 py-2.5"
                          style={{
                            background: "rgba(224,123,110,0.06)",
                            borderBottom: "1px solid rgba(224,123,110,0.18)",
                            borderLeft: "2px solid var(--fail)",
                          }}
                        >
                          <span className="t-micro font-mono" style={{ color: "var(--fail)", lineHeight: 1.6 }}>
                            {stepResult.detail}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Connection summary */}
              {connSummary.length > 0 && (
                <div style={{ width: 176, flexShrink: 0 }}>
                  <div className="border border-line p-4 space-y-3" style={{ background: "var(--bg-1)" }}>
                    <p className="t-micro font-medium uppercase" style={{ color: "var(--fg-3)", letterSpacing: "0.1em" }}>
                      connection
                    </p>
                    {connSummary.map(([k, v]) => (
                      <div key={k}>
                        <p className="t-micro" style={{ color: "var(--fg-3)" }}>{k}</p>
                        <p className="t-small font-mono" style={{ color: "var(--fg-0)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {v}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {healthError && (
              <div className="px-4 py-3 border" style={{ borderColor: "var(--fail)", background: "rgba(224,123,110,0.07)", color: "var(--fail)" }}>
                <p className="t-small">{healthError}</p>
              </div>
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex items-center gap-1.5 px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
                Back
              </button>

              {healthDone && !canProceedFromHealth() ? (
                <>
                  <button
                    onClick={runHealthCheck}
                    className="flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors hover:opacity-90"
                    style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
                  >
                    <RefreshCw size={12} strokeWidth={2} />
                    Retry Tests
                  </button>
                  <button
                    disabled
                    title="Fix connection issues to continue"
                    className="flex items-center gap-2 px-5 py-2.5 t-small font-medium border cursor-not-allowed"
                    style={{ background: "var(--bg-2)", color: "var(--fg-3)", borderColor: "var(--line)", opacity: 0.5 }}
                  >
                    Choose Datasets
                  </button>
                </>
              ) : (
                <button
                  onClick={handleAdvanceToStep3}
                  disabled={!canProceedFromHealth()}
                  className={clsx(
                    "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                    canProceedFromHealth() ? "hover:opacity-90" : "cursor-not-allowed opacity-40"
                  )}
                  style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
                >
                  {healthLoading && <Loader2 size={12} strokeWidth={2} className="animate-spin" />}
                  Choose Datasets
                </button>
              )}
            </div>
          </div>
        )}

        {/* ---- Step 3: Choose Datasets ---- */}
        {step === 3 && (
          <div className="space-y-5">
            <p className="t-small" style={{ color: "var(--fg-1)" }}>
              Select the datasets you want to monitor. You can change this later.
            </p>

            <div className="border border-line" style={{ background: "var(--bg-1)" }}>
              {tablesLoading ? (
                <div className="px-4 py-4 flex items-center gap-2 t-small" style={{ color: "var(--fg-2)" }}>
                  <Loader2 size={13} strokeWidth={1.6} className="animate-spin" />
                  Loading datasets...
                </div>
              ) : tables.length === 0 ? (
                <div className="px-4 py-4 t-small" style={{ color: "var(--fg-2)" }}>No datasets found.</div>
              ) : (
                tables.map((t, i) => (
                  <label
                    key={t.name}
                    className={clsx(
                      "flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors hover:bg-bg-2",
                      i > 0 && "border-t border-line"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={selectedTables.has(t.name)}
                      onChange={() => toggleTable(t.name)}
                      style={{ accentColor: "var(--accent)" }}
                    />
                    <span className="t-body font-mono" style={{ color: "var(--fg-0)" }}>{t.name}</span>
                    <span className="t-micro ml-auto" style={{ color: "var(--fg-3)" }}>{t.schema}</span>
                  </label>
                ))
              )}
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setStep(2)}
                className="flex items-center gap-1.5 px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
                Back
              </button>
              <button
                onClick={handleAdvanceToStep4}
                disabled={selectedTables.size === 0 || tablesLoading}
                className={clsx(
                  "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                  selectedTables.size > 0 && !tablesLoading ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
                )}
                style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
              >
                Review Checks
              </button>
              {selectedTables.size === 0 && !tablesLoading && (
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>Select at least one dataset</span>
              )}
            </div>
          </div>
        )}

        {/* ---- Step 4: Review Checks ---- */}
        {step === 4 && (
          <div className="space-y-5">
            <div className="flex items-center gap-2">
              <Sparkles size={13} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
              <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Suggested checks</span>
              {suggestLoading && (
                <Loader2 size={12} strokeWidth={1.6} className="animate-spin" style={{ color: "var(--fg-3)" }} />
              )}
            </div>

            {!suggestLoading && suggestions.length > 0 && (
              <div className="space-y-1">
                {(["essential", "recommended", "full_coverage"] as CheckTier[]).map((tier) => {
                  const active = activeTier === tier;
                  const count = suggestions.filter((s) => tierIncludes(tier, s.tier)).length;
                  return (
                    <button
                      key={tier}
                      onClick={() => handleTierChange(tier)}
                      className="w-full text-left px-3 py-2.5 border transition-colors"
                      style={{
                        borderColor: active ? "var(--accent)" : "var(--line)",
                        background: active ? "var(--accent-bg)" : "var(--bg-1)",
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="t-small font-medium" style={{ color: active ? "var(--accent)" : "var(--fg-0)" }}>
                          {TIER_LABELS[tier]}
                        </span>
                        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{count} checks</span>
                      </div>
                      <p className="t-micro mt-0.5" style={{ color: "var(--fg-2)", lineHeight: 1.4 }}>
                        {TIER_DESC[tier]}
                      </p>
                    </button>
                  );
                })}
              </div>
            )}

            {!suggestLoading && (
              <div className="border border-line" style={{ background: "var(--bg-1)", maxHeight: 280, overflowY: "auto" }}>
                {suggestions.length === 0 ? (
                  <div className="px-4 py-6 t-small text-center" style={{ color: "var(--fg-3)" }}>
                    No checks suggested. You can add checks manually later.
                  </div>
                ) : (
                  suggestions
                    .filter((s) => tierIncludes(activeTier, s.tier))
                    .map((s, i) => {
                      const key = `${s.table}.${s.column}.${s.detector_slug}`;
                      const checked = selectedChecks.has(key);
                      return (
                        <label
                          key={key}
                          className={clsx(
                            "flex items-start gap-3 px-3 py-2.5 cursor-pointer transition-colors hover:bg-bg-2",
                            i > 0 && "border-t border-line"
                          )}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleCheck(key)}
                            className="mt-0.5"
                            style={{ accentColor: "var(--accent)", flexShrink: 0 }}
                          />
                          <div className="min-w-0">
                            <p className="t-small font-mono" style={{ color: "var(--fg-0)" }}>
                              {s.table}.{s.column}
                              <span className="ml-2 t-micro" style={{ color: "var(--accent)" }}>{s.detector_slug}</span>
                            </p>
                            <p className="t-micro mt-0.5" style={{ color: "var(--fg-2)", lineHeight: 1.4 }}>
                              {s.rationale}
                            </p>
                          </div>
                        </label>
                      );
                    })
                )}
              </div>
            )}

            {!suggestLoading && suggestions.length > 0 && (
              <p className="t-micro" style={{ color: "var(--fg-3)" }}>
                {selectedChecks.size} of {suggestions.filter((s) => tierIncludes(activeTier, s.tier)).length} checks selected
              </p>
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={() => setStep(3)}
                className="flex items-center gap-1.5 px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
                Back
              </button>
              <button
                onClick={handleAdvanceToStep5}
                disabled={savingChecks || suggestLoading}
                className={clsx(
                  "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                  !savingChecks && !suggestLoading ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
                )}
                style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
              >
                {savingChecks ? "Saving..." : "Add Metrics"}
              </button>
            </div>
          </div>
        )}

        {/* ---- Step 5: Add Metrics ---- */}
        {step === 5 && (
          <div className="space-y-5">
            <div className="flex items-center gap-2">
              <TrendingUp size={13} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
              <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Add columns as metrics</span>
            </div>

            <p className="t-small" style={{ color: "var(--fg-1)", lineHeight: 1.5 }}>
              These columns have data quality checks. Add them to the semantic layer to track values over time and run causal analysis.
            </p>

            <div className="border border-line" style={{ background: "var(--bg-1)" }}>
              {checkedColumns().length === 0 ? (
                <div className="px-4 py-6 t-small text-center" style={{ color: "var(--fg-3)" }}>
                  No columns with checks to add as metrics.
                </div>
              ) : (
                checkedColumns().map((c, i) => {
                  const key = `${c.table}.${c.column}`;
                  const checked = selectedMetrics.has(key);
                  return (
                    <label
                      key={key}
                      className={clsx(
                        "flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-colors hover:bg-bg-2",
                        i > 0 && "border-t border-line"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleMetric(key)}
                        style={{ accentColor: "var(--accent)", flexShrink: 0 }}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="t-small font-mono" style={{ color: "var(--fg-0)" }}>
                          {c.table}.{c.column}
                        </p>
                      </div>
                      <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
                        {c.checkCount} {c.checkCount === 1 ? "check" : "checks"}
                      </span>
                    </label>
                  );
                })
              )}
            </div>

            {checkedColumns().length > 0 && (
              <p className="t-micro" style={{ color: "var(--fg-3)" }}>
                {selectedMetrics.size} of {checkedColumns().length} columns selected
              </p>
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={() => setStep(4)}
                className="flex items-center gap-1.5 px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
                Back
              </button>
              <button
                onClick={handleFinish}
                disabled={savingMetrics}
                className={clsx(
                  "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                  !savingMetrics ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
                )}
                style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
              >
                {savingMetrics ? "Saving..." : "Finish"}
              </button>
              <button
                onClick={() => router.push(`/sources/${activeSourceId}`)}
                className="px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                Skip
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

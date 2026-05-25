"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, Loader2, ChevronLeft, ChevronRight, X, Sparkles, TrendingUp, RefreshCw, Upload } from "lucide-react";
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
  // BigQuery: project is auto-detected from JSON key; no dataset field needed
  bigquery: [
    {
      key: "service_account_json",
      label: "Service Account Key",
      type: "textarea",
      placeholder: "",
      help: "The project ID is read from the key automatically.",
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
// Step types and wizard config
// ---------------------------------------------------------------------------

type StepId = "configure" | "verify" | "bq_datasets" | "tables" | "checks" | "metrics";
type CheckTier = "essential" | "recommended" | "full_coverage";

function getWizardSteps(engine: string): { id: StepId; label: string }[] {
  const steps: { id: StepId; label: string }[] = [
    { id: "configure", label: "Configure" },
    { id: "verify", label: "Test & Verify" },
  ];
  if (engine === "bigquery") {
    steps.push({ id: "bq_datasets", label: "Datasets" });
  }
  steps.push(
    { id: "tables", label: "Choose Tables" },
    { id: "checks", label: "Review Checks" },
    { id: "metrics", label: "Add Metrics" },
  );
  return steps;
}

const HEALTH_STEP_LABELS = ["TCP Reach", "Authentication", "Info Schema Read", "Sample SELECT", "Latency Probe"];

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

// ---------------------------------------------------------------------------
// JsonDropZone — file browse/drop or paste, with mode toggle
// ---------------------------------------------------------------------------

function JsonDropZone({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [mode, setMode] = useState<"file" | "paste">("file");
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const hasContent = value.trim().length > 0;

  const readFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (text) onChange(text);
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-2">
      {/* Mode toggle */}
      <div className="flex" style={{ gap: 0 }}>
        <button
          type="button"
          onClick={() => setMode("file")}
          className="px-3 py-1.5 t-micro border transition-colors"
          style={{
            background: mode === "file" ? "var(--accent-bg)" : "var(--bg-1)",
            color: mode === "file" ? "var(--accent)" : "var(--fg-3)",
            borderColor: mode === "file" ? "var(--accent)" : "var(--line)",
            borderRight: mode === "file" ? undefined : "none",
          }}
        >
          Browse / Drop
        </button>
        <button
          type="button"
          onClick={() => setMode("paste")}
          className="px-3 py-1.5 t-micro border transition-colors"
          style={{
            background: mode === "paste" ? "var(--accent-bg)" : "var(--bg-1)",
            color: mode === "paste" ? "var(--accent)" : "var(--fg-3)",
            borderColor: mode === "paste" ? "var(--accent)" : "var(--line)",
          }}
        >
          Paste JSON
        </button>
      </div>

      {mode === "file" ? (
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) readFile(file);
              e.target.value = "";
            }}
          />
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const file = e.dataTransfer.files[0];
              if (file) readFile(file);
            }}
            className="border border-dashed flex flex-col items-center justify-center py-6 gap-3 transition-colors"
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
              <>
                <span className="t-small" style={{ color: dragging ? "var(--accent)" : "var(--fg-3)" }}>
                  {dragging ? "Release to load" : "Drop key.json here"}
                </span>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2 t-small border transition-colors hover:opacity-80"
                  style={{ background: "var(--bg-2)", color: "var(--fg-1)", borderColor: "var(--line)" }}
                >
                  <Upload size={12} strokeWidth={1.6} />
                  Browse
                </button>
              </>
            )}
          </div>
          {hasContent && (
            <button
              type="button"
              onClick={() => onChange("")}
              className="t-micro mt-1 transition-colors hover:opacity-60"
              style={{ color: "var(--fg-3)" }}
            >
              Clear
            </button>
          )}
        </div>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={7}
          placeholder="Paste service account JSON here..."
          className="w-full px-4 py-3 border t-small font-mono outline-none resize-y"
          style={{
            background: "var(--bg-1)",
            color: "var(--fg-0)",
            borderColor: "var(--line)",
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Edit mode — simple form, no wizard steps
// ---------------------------------------------------------------------------

function EditSourceForm({
  engine,
  sourceId,
  initialName,
}: {
  engine: string;
  sourceId: string;
  initialName: string;
}) {
  const router = useRouter();
  const [name, setName] = useState(initialName);
  const [credential, setCredential] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const isBQ = engine === "bigquery";

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const body: Record<string, string> = {};
      if (name.trim()) body.name = name.trim();
      if (credential.trim()) body.password = credential.trim();
      const res = await fetch(`/api/v1/sources/${encodeURIComponent(sourceId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.detail || "Save failed");
        return;
      }
      router.back();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5" style={{ maxWidth: 480 }}>
      <div>
        <label className="block t-small mb-1.5 font-medium" style={{ color: "var(--fg-1)" }}>
          Connection name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-4 py-3 border t-body outline-none transition-colors"
          style={{ background: "var(--bg-1)", color: "var(--fg-0)", borderColor: "var(--line)" }}
        />
      </div>
      <div>
        <label className="block t-small mb-1.5 font-medium" style={{ color: "var(--fg-1)" }}>
          {isBQ ? "Service Account Key" : "Password"}
        </label>
        {isBQ ? (
          <JsonDropZone value={credential} onChange={setCredential} />
        ) : (
          <input
            type="password"
            value={credential}
            onChange={(e) => setCredential(e.target.value)}
            placeholder="Leave blank to keep existing"
            className="w-full px-4 py-3 border t-body outline-none transition-colors"
            style={{ background: "var(--bg-1)", color: "var(--fg-0)", borderColor: "var(--line)" }}
          />
        )}
      </div>
      {error && <p className="t-small" style={{ color: "var(--fail)" }}>{error}</p>}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className={clsx(
            "px-5 py-2.5 t-small font-medium border transition-colors",
            !saving ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
          )}
          style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          onClick={() => router.back()}
          className="px-3 py-2.5 t-small transition-colors hover:opacity-60"
          style={{ color: "var(--fg-2)" }}
        >
          Cancel
        </button>
      </div>
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

interface MetricSuggestion {
  name: string;
  definition: string;
  sql_expression: string;
  numerator_columns: string[];
  denominator_columns: string[];
  grain: string;
  aggregation: string;
  additivity: "full" | "semi" | "non";
  kind: "ratio" | "count" | "sum";
  good_direction: "up" | "down" | "in_band";
  suggested_owner_role: string;
  guardrail_for: string | null;
  cadence: string;
  confidence: number;
  reasoning: string;
  source_column: string;
  dataset: string;
  display_name: string;
}

interface RejectedCandidate {
  column: string;
  reason: string;
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

// Thin dispatcher — avoids hooks-after-conditional-return
export function Wizard(props: WizardProps) {
  if (props.mode === "edit" && props.sourceId) {
    return (
      <EditSourceForm
        engine={props.engine}
        sourceId={props.sourceId}
        initialName={props.initialValues?.name ?? ""}
      />
    );
  }
  return <WizardCreate {...props} />;
}

function WizardCreate({ engine, sourceId, initialValues = {}, mode = "create" }: WizardProps) {
  const router = useRouter();
  const sessionKey = `wizard-draft-${engine}`;
  const isBQ = engine === "bigquery";

  const wizardSteps = getWizardSteps(engine);

  const [step, setStep] = useState<StepId>("configure");
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
    if (step !== "configure") return;
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

  // Tables + BQ datasets state
  const [tables, setTables] = useState<TableItem[]>([]);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [selectedBQDatasets, setSelectedBQDatasets] = useState<Set<string>>(new Set());
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set());

  // Step 4 state
  const [suggestions, setSuggestions] = useState<CheckSuggestion[]>([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [activeTier, setActiveTier] = useState<CheckTier>("recommended");
  // Keys use "::" separator: "table::column::detector_slug"
  const [selectedChecks, setSelectedChecks] = useState<Set<string>>(new Set());
  const [savingChecks, setSavingChecks] = useState(false);

  // Step 5 state
  const [metricSuggestions, setMetricSuggestions] = useState<MetricSuggestion[]>([]);
  const [rejectedCandidates, setRejectedCandidates] = useState<RejectedCandidate[]>([]);
  const [metricSuggestLoading, setMetricSuggestLoading] = useState(false);
  const [showRejected, setShowRejected] = useState(false);
  const [selectedMetrics, setSelectedMetrics] = useState<Set<string>>(new Set());
  const [savingMetrics, setSavingMetrics] = useState(false);

  const runHealthCheck = useCallback(async () => {
    setHealthSteps([]);
    setHealthDone(false);
    setHealthPassed(false);
    setHealthLoading(true);
    setHealthError(null);

    try {
      const host = isBQ
        ? (formValues.project || "")
        : (formValues.url || formValues.host || formValues.account || "");
      const port = isBQ ? 0 : parseInt(formValues.port || "8443", 10);
      const dbName = isBQ ? "" : (formValues.database || formValues.project || "default");
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
  }, [engine, formValues, isBQ]);

  useEffect(() => {
    if (step === "verify") runHealthCheck();
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

  // Fetch tables when entering bq_datasets (BQ) or tables (non-BQ) step
  useEffect(() => {
    const shouldFetch =
      (isBQ && step === "bq_datasets") ||
      (!isBQ && step === "tables");
    if (!shouldFetch || !activeSourceId) return;
    setTablesLoading(true);
    fetch(`/api/v1/sources/${encodeURIComponent(activeSourceId)}/tables`)
      .then((r) => r.ok ? r.json() : [])
      .then((data: TableItem[]) => {
        setTables(data);
        if (isBQ) {
          // Pre-select all BQ datasets
          const schemas = new Set(data.map((t) => t.schema).filter(Boolean));
          setSelectedBQDatasets(schemas);
        } else {
          setSelectedTables(new Set(data.filter((t) => t.watched).map((t) => t.name)));
        }
      })
      .catch(() => setTables([]))
      .finally(() => setTablesLoading(false));
  }, [step, activeSourceId, isBQ]);

  async function handleAdvanceToVerify() {
    if (mode === "create" && !activeSourceId) {
      const host = isBQ
        ? (formValues.project || "")
        : (formValues.url || formValues.host || formValues.account || "");
      const port = isBQ ? 0 : parseInt(formValues.port || "8443", 10);
      const dbName = isBQ ? "" : (formValues.database || formValues.project || "default");
      const password = isBQ ? (formValues.service_account_json || "") : (formValues.password || "");
      const name = connectionName.trim() || (isBQ ? `bigquery://${host || "project"}` : `${engine}://${host}`);
      try {
        const res = await fetch("/api/v1/sources", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name, engine, host,
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
    setStep("verify");
  }

  function handleAdvanceAfterVerify() {
    setStep(isBQ ? "bq_datasets" : "tables");
  }

  function handleAdvanceToTables() {
    // For BQ: filter tables to those in selectedBQDatasets
    if (isBQ) {
      const filtered = tables
        .filter((t) => selectedBQDatasets.has(t.schema))
        .map((t) => `${t.schema}.${t.name}`);
      setSelectedTables(new Set(filtered));
    }
    setStep("tables");
  }

  async function handleAdvanceToChecks() {
    if (!activeSourceId) { setStep("checks"); return; }

    // Save selected tables — for BQ, keys are "schema.table"
    await fetch(`/api/v1/sources/${encodeURIComponent(activeSourceId)}/tables`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tables: Array.from(selectedTables) }),
    }).catch(() => null);

    setSuggestLoading(true);
    setStep("checks");
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
        // Default activeTier is "recommended" — pre-select essential + recommended
        const keys = new Set(
          data
            .filter((s) => tierIncludes("recommended", s.tier))
            .map((s) => `${s.table}::${s.column}::${s.detector_slug}`)
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
        .map((s) => `${s.table}::${s.column}::${s.detector_slug}`)
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

  // Parse check keys "table::column::detector" to get unique table/column pairs
  function checkedColumns(): Array<{ table: string; column: string; checkCount: number }> {
    const map = new Map<string, number>();
    selectedChecks.forEach((key) => {
      const parts = key.split("::");
      if (parts.length < 3) return;
      const colKey = `${parts[0]}::${parts[1]}`;
      map.set(colKey, (map.get(colKey) ?? 0) + 1);
    });
    return Array.from(map.entries()).map(([k, count]) => {
      const sep = k.indexOf("::");
      return { table: k.slice(0, sep), column: k.slice(sep + 2), checkCount: count };
    });
  }

  async function handleAdvanceToMetrics() {
    if (!activeSourceId) { router.push("/sources"); return; }
    setSavingChecks(true);
    setStep("metrics");
    setMetricSuggestLoading(true);
    setMetricSuggestions([]);
    setRejectedCandidates([]);
    setSelectedMetrics(new Set());
    try {
      if (selectedChecks.size > 0) {
        const checksToSave = suggestions
          .filter((s) => selectedChecks.has(`${s.table}::${s.column}::${s.detector_slug}`))
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
      if (cols.length > 0) {
        try {
          const res = await fetch("/api/v1/metrics/suggest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              columns: cols.map((c) => ({ dataset: c.table, column: c.column })),
            }),
          });
          if (res.ok) {
            const data = await res.json();
            const fetched: MetricSuggestion[] = data.metrics ?? [];
            setMetricSuggestions(fetched);
            setRejectedCandidates(data.rejected_candidates ?? []);
            setSelectedMetrics(new Set(
              fetched.filter((m) => m.confidence >= 0.65).map((m) => m.source_column)
            ));
          }
        } catch { /* empty — user can still finish */ }
      }
    } finally {
      setSavingChecks(false);
      setMetricSuggestLoading(false);
    }
  }

  function inferKind(col: string): "ratio" | "count" | "sum" {
    const n = col.toLowerCase();
    if (/^(n_|count_|num_)/.test(n) || /(_count|_n|_number)$/.test(n)) return "count";
    if (/^(sum_|total_)/.test(n) || /(_sum|_total)$/.test(n)) return "sum";
    return "ratio";
  }

  async function handleFinish() {
    if (!activeSourceId) { router.push("/sources"); return; }
    setSavingMetrics(true);
    try {
      const toSave = metricSuggestions
        .filter((m) => selectedMetrics.has(m.source_column))
        .map((m) => ({
          display_name: m.display_name || m.name,
          kind: m.kind || inferKind(m.source_column.split(".").pop() ?? ""),
          dataset: m.dataset,
          description: m.definition,
          owners: m.suggested_owner_role ? [m.suggested_owner_role] : [],
          tags: [m.cadence, m.additivity].filter(Boolean),
          source_id: activeSourceId ?? null,
          column_name: m.source_column.split(".").pop() ?? m.source_column,
        }));
      if (toSave.length > 0) {
        await fetch("/api/v1/metrics/batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ metrics: toSave }),
        }).catch(() => null);
      }
      router.push("/sources");
    } finally {
      setSavingMetrics(false);
    }
  }

  function toggleTable(key: string) {
    setSelectedTables((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleBQDataset(schema: string) {
    setSelectedBQDatasets((prev) => {
      const next = new Set(prev);
      if (next.has(schema)) next.delete(schema);
      else next.add(schema);
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
      // Auto-detect project from BQ JSON
      if (key === "service_account_json" && engine === "bigquery") {
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
    ["database", formValues.database || ""],
    ["user", formValues.username || ""],
  ].filter(([, v]) => v) as [string, string][];

  // Stepper helpers
  const currentStepIndex = wizardSteps.findIndex((s) => s.id === step);

  // BQ datasets derived from tables
  const bqDatasets = Array.from(new Set(tables.map((t) => t.schema).filter(Boolean))).sort();

  // Tables filtered for "tables" step when BQ
  const visibleTables = isBQ
    ? tables.filter((t) => selectedBQDatasets.has(t.schema))
    : tables;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex gap-10">
      {/* Vertical stepper */}
      <div style={{ width: 148, flexShrink: 0, paddingTop: 2 }}>
        {wizardSteps.map((s, idx) => {
          const active = step === s.id;
          const done = idx < currentStepIndex;
          return (
            <div key={s.id} className="flex gap-3">
              <div className="flex flex-col items-center" style={{ width: 20 }}>
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
                      {idx + 1}
                    </span>
                  </div>
                )}
                {idx < wizardSteps.length - 1 && (
                  <div style={{ width: 1, height: 36, background: done ? "var(--accent)" : "var(--line)", opacity: done ? 0.3 : 1 }} />
                )}
              </div>
              {/* Label aligned to center of the 20px circle */}
              <div style={{ height: 20, display: "flex", alignItems: "center" }}>
                <span
                  style={{
                    fontSize: 12,
                    color: active ? "var(--fg-0)" : done ? "var(--fg-2)" : "var(--fg-3)",
                    fontWeight: active ? 500 : 400,
                    fontFamily: "var(--font-jetbrains-mono)",
                    lineHeight: 1,
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

        {/* ---- Configure ---- */}
        {step === "configure" && (
          <div className="space-y-5" style={{ maxWidth: 520 }}>
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
                onClick={handleAdvanceToVerify}
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
        )}

        {/* ---- Test & Verify ---- */}
        {step === "verify" && (
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
                            width: 20, height: 20,
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
                onClick={() => setStep("configure")}
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
                    Retry
                  </button>
                  <button
                    disabled
                    className="flex items-center gap-2 px-5 py-2.5 t-small font-medium border cursor-not-allowed"
                    style={{ background: "var(--bg-2)", color: "var(--fg-3)", borderColor: "var(--line)", opacity: 0.5 }}
                  >
                    {isBQ ? "Choose Datasets" : "Choose Tables"}
                    <ChevronRight size={13} strokeWidth={2} />
                  </button>
                </>
              ) : (
                <button
                  onClick={handleAdvanceAfterVerify}
                  disabled={!canProceedFromHealth()}
                  className={clsx(
                    "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                    canProceedFromHealth() ? "hover:opacity-90" : "cursor-not-allowed opacity-40"
                  )}
                  style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
                >
                  {healthLoading && <Loader2 size={12} strokeWidth={2} className="animate-spin" />}
                  {isBQ ? "Choose Datasets" : "Choose Tables"}
                  {!healthLoading && <ChevronRight size={13} strokeWidth={2} />}
                </button>
              )}
            </div>
          </div>
        )}

        {/* ---- BQ Datasets (BigQuery only) ---- */}
        {step === "bq_datasets" && (
          <div className="space-y-5">
            <p className="t-small" style={{ color: "var(--fg-1)" }}>
              Select the BigQuery datasets to watch. Only tables from the selected datasets will be available in the next step.
            </p>

            <div className="border border-line" style={{ background: "var(--bg-1)" }}>
              {tablesLoading ? (
                <div className="px-4 py-4 flex items-center gap-2 t-small" style={{ color: "var(--fg-2)" }}>
                  <Loader2 size={13} strokeWidth={1.6} className="animate-spin" />
                  Loading datasets...
                </div>
              ) : bqDatasets.length === 0 ? (
                <div className="px-4 py-4 t-small" style={{ color: "var(--fg-2)" }}>No datasets found.</div>
              ) : (
                bqDatasets.map((schema, i) => (
                  <label
                    key={schema}
                    className={clsx(
                      "flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors hover:bg-bg-2",
                      i > 0 && "border-t border-line"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={selectedBQDatasets.has(schema)}
                      onChange={() => toggleBQDataset(schema)}
                      style={{ accentColor: "var(--accent)" }}
                    />
                    <span className="t-body font-mono" style={{ color: "var(--fg-0)" }}>{schema}</span>
                  </label>
                ))
              )}
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setStep("verify")}
                className="flex items-center gap-1.5 px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
                Back
              </button>
              <button
                onClick={handleAdvanceToTables}
                disabled={selectedBQDatasets.size === 0 || tablesLoading}
                className={clsx(
                  "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                  selectedBQDatasets.size > 0 && !tablesLoading ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
                )}
                style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
              >
                Choose Tables
                <ChevronRight size={13} strokeWidth={2} />
              </button>
              {selectedBQDatasets.size === 0 && !tablesLoading && (
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>Select at least one dataset</span>
              )}
            </div>
          </div>
        )}

        {/* ---- Choose Tables ---- */}
        {step === "tables" && (
          <div className="space-y-5">
            <p className="t-small" style={{ color: "var(--fg-1)" }}>
              Select the tables you want to monitor. You can change this later.
            </p>

            <div className="border border-line" style={{ background: "var(--bg-1)" }}>
              {tablesLoading ? (
                <div className="px-4 py-4 flex items-center gap-2 t-small" style={{ color: "var(--fg-2)" }}>
                  <Loader2 size={13} strokeWidth={1.6} className="animate-spin" />
                  Loading tables...
                </div>
              ) : visibleTables.length === 0 ? (
                <div className="px-4 py-4 t-small" style={{ color: "var(--fg-2)" }}>No tables found.</div>
              ) : (
                visibleTables.map((t, i) => {
                  const key = isBQ ? `${t.schema}.${t.name}` : t.name;
                  return (
                    <label
                      key={key}
                      className={clsx(
                        "flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors hover:bg-bg-2",
                        i > 0 && "border-t border-line"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selectedTables.has(key)}
                        onChange={() => toggleTable(key)}
                        style={{ accentColor: "var(--accent)" }}
                      />
                      <span className="t-body font-mono" style={{ color: "var(--fg-0)" }}>{key}</span>
                    </label>
                  );
                })
              )}
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setStep(isBQ ? "bq_datasets" : "verify")}
                className="flex items-center gap-1.5 px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
                Back
              </button>
              <button
                onClick={handleAdvanceToChecks}
                disabled={selectedTables.size === 0 || tablesLoading}
                className={clsx(
                  "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                  selectedTables.size > 0 && !tablesLoading ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
                )}
                style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
              >
                Review Checks
                <ChevronRight size={13} strokeWidth={2} />
              </button>
              {selectedTables.size === 0 && !tablesLoading && (
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>Select at least one table</span>
              )}
            </div>
          </div>
        )}

        {/* ---- Review Checks ---- */}
        {step === "checks" && (
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
                      const key = `${s.table}::${s.column}::${s.detector_slug}`;
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
                onClick={() => setStep("tables")}
                className="flex items-center gap-1.5 px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
                Back
              </button>
              <button
                onClick={handleAdvanceToMetrics}
                disabled={savingChecks || suggestLoading}
                className={clsx(
                  "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                  !savingChecks && !suggestLoading ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
                )}
                style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
              >
                {savingChecks ? "Saving..." : <><span>Add Metrics</span><ChevronRight size={13} strokeWidth={2} /></>}
              </button>
            </div>
          </div>
        )}

        {/* ---- Add Metrics ---- */}
        {step === "metrics" && (
          <div className="space-y-5">
            <div className="flex items-center gap-2">
              <Sparkles size={13} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
              <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Suggested metrics</span>
              {metricSuggestLoading && (
                <Loader2 size={12} strokeWidth={1.6} className="animate-spin" style={{ color: "var(--fg-3)" }} />
              )}
            </div>

            {!metricSuggestLoading && (
              <>
                <p className="t-micro" style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>
                  Columns classified as measure candidates via heuristics and AI judgment.
                  Pre-selected where confidence is high — deselect any you don&apos;t need.
                </p>

                <div className="border border-line" style={{ background: "var(--bg-1)" }}>
                  {metricSuggestions.length === 0 ? (
                    <div className="px-4 py-6 t-small text-center" style={{ color: "var(--fg-3)" }}>
                      No measure candidates found in these columns. You can add metrics manually later.
                    </div>
                  ) : (
                    metricSuggestions.map((m, i) => {
                      const checked = selectedMetrics.has(m.source_column);
                      const addColor =
                        m.additivity === "full" ? "var(--pass)" :
                        m.additivity === "semi" ? "var(--warn)" : "var(--fg-3)";
                      return (
                        <label
                          key={m.source_column}
                          className={clsx(
                            "flex items-start gap-3 px-3 py-3 cursor-pointer transition-colors hover:bg-bg-2",
                            i > 0 && "border-t border-line"
                          )}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleMetric(m.source_column)}
                            className="mt-0.5"
                            style={{ accentColor: "var(--accent)", flexShrink: 0 }}
                          />
                          <div className="min-w-0 flex-1 space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>
                                {m.name}
                              </span>
                              <span
                                className="t-micro font-mono px-1.5 py-0.5 border"
                                style={{ borderColor: "var(--accent)", color: "var(--accent)", background: "var(--accent-bg)", fontSize: 10 }}
                              >
                                {m.kind}
                              </span>
                              <span
                                className="t-micro font-mono px-1.5 py-0.5 border"
                                style={{ borderColor: addColor, color: addColor, fontSize: 10 }}
                              >
                                {m.additivity}
                              </span>
                              <span className="t-micro font-mono" style={{ color: "var(--fg-3)", fontSize: 10 }}>
                                {Math.round(m.confidence * 100)}%
                              </span>
                              {m.guardrail_for && (
                                <span
                                  className="t-micro px-1 border"
                                  style={{ borderColor: "var(--line)", color: "var(--fg-3)", fontSize: 10 }}
                                >
                                  guardrail for {m.guardrail_for}
                                </span>
                              )}
                            </div>
                            <p className="t-micro" style={{ color: "var(--fg-2)", lineHeight: 1.4 }}>
                              {m.definition}
                            </p>
                            <p className="t-micro font-mono" style={{ color: "var(--fg-3)", fontSize: 10 }}>
                              {m.source_column}
                              {m.cadence && (
                                <span style={{ marginLeft: 8 }}>{m.cadence}</span>
                              )}
                            </p>
                          </div>
                        </label>
                      );
                    })
                  )}
                </div>

                {metricSuggestions.length > 0 && (
                  <p className="t-micro" style={{ color: "var(--fg-3)" }}>
                    {selectedMetrics.size} of {metricSuggestions.length} selected
                  </p>
                )}

                {rejectedCandidates.length > 0 && (
                  <div>
                    <button
                      type="button"
                      onClick={() => setShowRejected((v) => !v)}
                      className="t-micro transition-opacity hover:opacity-70"
                      style={{ color: "var(--fg-3)" }}
                    >
                      {showRejected ? "Hide" : "Show"} {rejectedCandidates.length} filtered-out columns
                    </button>
                    {showRejected && (
                      <div className="mt-2 border border-line" style={{ background: "var(--bg-1)" }}>
                        {rejectedCandidates.map((r, i) => (
                          <div
                            key={r.column}
                            className={clsx("px-3 py-1.5 flex items-center justify-between", i > 0 && "border-t border-line")}
                          >
                            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{r.column}</span>
                            <span className="t-micro" style={{ color: "var(--fg-3)", opacity: 0.6 }}>{r.reason}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={() => setStep("checks")}
                className="flex items-center gap-1.5 px-3 py-2.5 t-small transition-colors hover:opacity-60"
                style={{ color: "var(--fg-2)" }}
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
                Back
              </button>
              <button
                onClick={handleFinish}
                disabled={savingMetrics || metricSuggestLoading}
                className={clsx(
                  "flex items-center gap-2 px-5 py-2.5 t-small font-medium border transition-colors",
                  !savingMetrics && !metricSuggestLoading ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
                )}
                style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
              >
                {savingMetrics ? "Saving..." : "Finish"}
              </button>
              <button
                onClick={() => router.push("/sources")}
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

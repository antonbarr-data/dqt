"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Check, Loader2, ChevronLeft, X, Sparkles, TrendingUp } from "lucide-react";
import { clsx } from "clsx";

type FieldDef = {
  key: string;
  label: string;
  type: "text" | "password" | "textarea" | "toggle";
  placeholder: string;
};

const ENGINE_FIELDS: Record<string, FieldDef[]> = {
  postgres: [
    { key: "host", label: "Host", type: "text", placeholder: "db.example.com" },
    { key: "port", label: "Port", type: "text", placeholder: "5432" },
    { key: "database", label: "Database", type: "text", placeholder: "production" },
    { key: "username", label: "Username", type: "text", placeholder: "dqt_readonly" },
    { key: "password", label: "Password", type: "password", placeholder: "" },
  ],
  mysql: [
    { key: "host", label: "Host", type: "text", placeholder: "db.example.com" },
    { key: "port", label: "Port", type: "text", placeholder: "3306" },
    { key: "database", label: "Database", type: "text", placeholder: "production" },
    { key: "username", label: "Username", type: "text", placeholder: "dqt_readonly" },
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
    { key: "project", label: "GCP Project ID", type: "text", placeholder: "my-project-123" },
    { key: "dataset", label: "Dataset", type: "text", placeholder: "Leave blank to scan all" },
    { key: "service_account_json", label: "Service Account JSON", type: "textarea", placeholder: "Paste JSON key or upload file" },
  ],
  snowflake: [
    { key: "account", label: "Account", type: "text", placeholder: "myaccount.us-east-1" },
    { key: "database", label: "Database", type: "text", placeholder: "PRODUCTION" },
    { key: "warehouse", label: "Warehouse", type: "text", placeholder: "DQT_WH" },
    { key: "username", label: "Username", type: "text", placeholder: "DQT_READONLY" },
    { key: "password", label: "Password", type: "password", placeholder: "" },
  ],
};

type Step = 1 | 2 | 3 | 4 | 5;
type CheckTier = "essential" | "recommended" | "full_coverage";

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

const STEP_LABELS = ["TCP Reach", "Authentication", "Info Schema Read", "Sample SELECT", "Latency Probe", "Clock Skew"];
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

function tierIncludes(activeTier: CheckTier, itemTier: CheckTier): boolean {
  const order: CheckTier[] = ["essential", "recommended", "full_coverage"];
  return order.indexOf(itemTier) <= order.indexOf(activeTier);
}

export function Wizard({ engine, sourceId, initialValues = {}, mode = "create" }: WizardProps) {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [connectionName, setConnectionName] = useState(initialValues.name ?? "");
  const [activeSourceId, setActiveSourceId] = useState<string | undefined>(sourceId);

  const fields = ENGINE_FIELDS[engine] ?? ENGINE_FIELDS["postgres"];
  const [formValues, setFormValues] = useState<Record<string, string>>(() => {
    const defaults: Record<string, string> = {};
    for (const f of fields) defaults[f.key] = initialValues[f.key] ?? "";
    return defaults;
  });

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
      const password = isBQ
        ? (formValues.service_account_json || "")
        : (formValues.password || "");

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
      const password = isBQ
        ? (formValues.service_account_json || "")
        : (formValues.password || "");
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

  // Columns that have at least one selected check -- candidates for metrics
  function checkedColumns(): Array<{ table: string; column: string; checkCount: number }> {
    const map = new Map<string, number>();
    selectedChecks.forEach((key) => {
      const parts = key.split(".");
      // key format: table.column.detector_slug -- column may contain dots
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
      // Pre-select all checked columns as metrics
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
    setFormValues((prev) => ({ ...prev, [key]: value }));
  }

  const stepLabels = ["Configure", "Test & Verify", "Choose Datasets", "Review Checks", "Add Metrics"] as const;

  return (
    <div className="max-w-lg">
      {/* step indicator */}
      <div className="flex items-center gap-0 mb-6 flex-wrap gap-y-2">
        {stepLabels.map((label, idx) => {
          const n = (idx + 1) as Step;
          const active = step === n;
          const done = step > n;
          return (
            <div key={label} className="flex items-center">
              <div className="flex items-center gap-1.5">
                <div
                  className="w-5 h-5 flex items-center justify-center t-micro font-mono border"
                  style={{
                    borderColor: active || done ? "var(--accent)" : "var(--line)",
                    background: done ? "var(--accent)" : active ? "var(--accent-bg)" : "var(--bg-2)",
                    color: done ? "var(--bg-0)" : active ? "var(--accent)" : "var(--fg-2)",
                  }}
                >
                  {done ? <Check size={10} strokeWidth={2.5} /> : n}
                </div>
                <span className="t-small" style={{ color: active ? "var(--fg-0)" : "var(--fg-2)" }}>
                  {label}
                </span>
              </div>
              {idx < stepLabels.length - 1 && (
                <div className="mx-2" style={{ width: 20, height: 1, background: "var(--line)" }} />
              )}
            </div>
          );
        })}
      </div>

      {/* ---- Step 1: Configure ---- */}
      {step === 1 && (
        <div className="space-y-4">
          <div>
            <label className="block t-small mb-1" style={{ color: "var(--fg-1)" }}>Connection name</label>
            <input
              type="text"
              value={connectionName}
              onChange={(e) => setConnectionName(e.target.value)}
              placeholder={`My ${engine} connection`}
              className="w-full px-3 py-2 border border-line t-body outline-none"
              style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
            />
          </div>

          {fields.map((f) =>
            f.type === "textarea" ? (
              <div key={f.key}>
                <label className="block t-small mb-1" style={{ color: "var(--fg-1)" }}>{f.label}</label>
                <textarea
                  value={formValues[f.key] ?? ""}
                  onChange={(e) => setField(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  rows={5}
                  className="w-full px-3 py-2 border border-line t-small font-mono outline-none resize-none"
                  style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
                />
              </div>
            ) : f.type === "toggle" ? (
              <div key={f.key} className="flex items-center justify-between">
                <span className="t-small" style={{ color: "var(--fg-1)" }}>{f.label}</span>
                <button
                  type="button"
                  onClick={() => setField(f.key, formValues[f.key] === "true" ? "false" : "true")}
                  className="flex items-center gap-2 px-3 py-1.5 border t-small transition-colors"
                  style={{
                    borderColor: formValues[f.key] === "true" ? "var(--accent)" : "var(--line)",
                    background: formValues[f.key] === "true" ? "var(--accent-bg)" : "var(--bg-2)",
                    color: formValues[f.key] === "true" ? "var(--accent)" : "var(--fg-2)",
                  }}
                >
                  {formValues[f.key] === "true" ? "Yes" : "No"}
                </button>
              </div>
            ) : (
              <div key={f.key}>
                <label className="block t-small mb-1" style={{ color: "var(--fg-1)" }}>{f.label}</label>
                <input
                  type={f.type}
                  value={formValues[f.key] ?? ""}
                  onChange={(e) => setField(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  className="w-full px-3 py-2 border border-line t-body outline-none"
                  style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
                />
              </div>
            )
          )}

          <button
            onClick={() => setStep(2)}
            className="flex items-center gap-2 px-4 py-2 t-small font-medium border transition-colors hover:opacity-90"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
          >
            Test Connection
          </button>
        </div>
      )}

      {/* ---- Step 2: Test & Verify ---- */}
      {step === 2 && (
        <div className="space-y-5">
          <div className="space-y-2">
            {STEP_LABELS.map((label, i) => {
              const stepResult = healthSteps[i];
              const isActive = !healthDone && healthSteps.length === i && healthLoading;
              const done = !!stepResult;
              const statusColor =
                stepResult?.status === "fail" ? "var(--fail)" :
                stepResult?.status === "skip" ? "var(--fg-2)" :
                "var(--pass)";
              return (
                <div key={label} className="flex items-center gap-3">
                  <div
                    className="w-5 h-5 flex items-center justify-center border"
                    style={{
                      borderColor: done ? statusColor : "var(--line)",
                      background: done ? statusColor : "var(--bg-2)",
                    }}
                  >
                    {done ? (
                      stepResult.status === "fail" ? (
                        <X size={11} strokeWidth={2.5} style={{ color: "var(--bg-0)" }} />
                      ) : (
                        <Check size={11} strokeWidth={2.5} style={{ color: "var(--bg-0)" }} />
                      )
                    ) : isActive ? (
                      <Loader2 size={11} strokeWidth={2} className="animate-spin" style={{ color: "var(--fg-2)" }} />
                    ) : null}
                  </div>
                  <span className="t-body" style={{ color: done ? "var(--fg-0)" : "var(--fg-2)" }}>
                    {label}
                  </span>
                  {done && stepResult.latency_ms > 0 && (
                    <span className="t-micro font-mono ml-auto" style={{ color: "var(--fg-3)" }}>
                      {stepResult.latency_ms}ms
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {healthError && (
            <p className="t-small" style={{ color: "var(--fail)" }}>{healthError}</p>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => setStep(1)}
              className="flex items-center gap-1.5 px-3 py-2 t-small border border-line transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-1)" }}
            >
              <ChevronLeft size={13} strokeWidth={1.6} />
              Back
            </button>
            <button
              onClick={handleAdvanceToStep3}
              disabled={!healthDone || !healthPassed}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 t-small font-medium border transition-colors",
                healthDone && healthPassed ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
              )}
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
            >
              Choose Datasets
            </button>
            {healthDone && !healthPassed && (
              <button
                onClick={runHealthCheck}
                className="px-3 py-2 t-small border border-line transition-colors hover:bg-bg-2"
                style={{ color: "var(--fg-1)" }}
              >
                Retry
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
              className="flex items-center gap-1.5 px-3 py-2 t-small border border-line transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-1)" }}
            >
              <ChevronLeft size={13} strokeWidth={1.6} />
              Back
            </button>
            <button
              onClick={handleAdvanceToStep4}
              disabled={selectedTables.size === 0 || tablesLoading}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 t-small font-medium border transition-colors",
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

          {/* Tier filter */}
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

          {/* Check list */}
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
              className="flex items-center gap-1.5 px-3 py-2 t-small border border-line transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-1)" }}
            >
              <ChevronLeft size={13} strokeWidth={1.6} />
              Back
            </button>
            <button
              onClick={handleAdvanceToStep5}
              disabled={savingChecks || suggestLoading}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 t-small font-medium border transition-colors",
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
              className="flex items-center gap-1.5 px-3 py-2 t-small border border-line transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-1)" }}
            >
              <ChevronLeft size={13} strokeWidth={1.6} />
              Back
            </button>
            <button
              onClick={handleFinish}
              disabled={savingMetrics}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 t-small font-medium border transition-colors",
                !savingMetrics ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
              )}
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
            >
              {savingMetrics ? "Saving..." : "Finish"}
            </button>
            <button
              onClick={() => router.push(`/sources/${activeSourceId}`)}
              className="px-3 py-2 t-small border border-line transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-1)" }}
            >
              Skip
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

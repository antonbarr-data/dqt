"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Check, Loader2, ChevronLeft, X } from "lucide-react";
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

type Step = 1 | 2 | 3;

interface HealthStep {
  name: string;
  display: string;
  status: "pass" | "fail" | "skip";
  latency_ms: number;
  detail: string;
}

interface TableItem { name: string; schema: string; watched: boolean }

interface WizardProps {
  engine: string;
  sourceId?: string;
  initialValues?: Record<string, string>;
  mode?: "create" | "edit";
}

const STEP_LABELS = ["TCP Reach", "Authentication", "Info Schema Read", "Sample SELECT", "Latency Probe", "Clock Skew"];

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
  const [saving, setSaving] = useState(false);
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set());

  const runHealthCheck = useCallback(async () => {
    setHealthSteps([]);
    setHealthDone(false);
    setHealthPassed(false);
    setHealthLoading(true);
    setHealthError(null);

    try {
      const host = formValues.url || formValues.host || formValues.account || "";
      const port = parseInt(formValues.port || "8443", 10);
      const dbName = formValues.database || formValues.project || "default";

      const res = await fetch("/api/v1/sources/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engine,
          host,
          port: isNaN(port) ? 8443 : port,
          username: formValues.username || "",
          password: formValues.password || "",
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
      setHealthError("Network error — could not reach server");
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
      const host = formValues.url || formValues.host || formValues.account || "";
      const port = parseInt(formValues.port || "8443", 10);
      const dbName = formValues.database || formValues.project || "default";
      const name = connectionName.trim() || `${engine}://${host}`;

      try {
        const res = await fetch("/api/v1/sources", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            engine,
            host,
            port: isNaN(port) ? 8443 : port,
            username: formValues.username || "",
            password: formValues.password || "",
            secure: formValues.secure === "true",
            db_name: dbName,
          }),
        });
        if (res.ok) {
          const created = await res.json();
          setActiveSourceId(created.id);
        }
      } catch {
        // proceed to step 3 regardless; tables fetch will fail gracefully
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

  async function handleFinish() {
    if (!activeSourceId) { router.push("/sources"); return; }
    setSaving(true);
    try {
      await fetch(`/api/v1/sources/${encodeURIComponent(activeSourceId)}/tables`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tables: Array.from(selectedTables) }),
      });
      router.push(`/sources/${activeSourceId}`);
    } finally {
      setSaving(false);
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

  function setField(key: string, value: string) {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="max-w-lg">
      {/* step indicator */}
      <div className="flex items-center gap-0 mb-6">
        {(["Configure", "Test & Verify", "Choose Tables"] as const).map((label, idx) => {
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
              {idx < 2 && (
                <div className="mx-2" style={{ width: 20, height: 1, background: "var(--line)" }} />
              )}
            </div>
          );
        })}
      </div>

      {/* ---- Step 1: Configure ---- */}
      {step === 1 && (
        <div className="space-y-4">
          {/* Connection name — common field */}
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
            Test Connection →
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
              Configure Tables →
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

      {/* ---- Step 3: Choose Tables ---- */}
      {step === 3 && (
        <div className="space-y-5">
          <p className="t-small" style={{ color: "var(--fg-1)" }}>
            Select tables to watch. You can change this later.
          </p>

          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            {tablesLoading ? (
              <div className="px-4 py-4 t-small" style={{ color: "var(--fg-2)" }}>Loading tables...</div>
            ) : tables.length === 0 ? (
              <div className="px-4 py-4 t-small" style={{ color: "var(--fg-2)" }}>No tables found.</div>
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
              onClick={handleFinish}
              disabled={saving}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 t-small font-medium border transition-colors",
                saving ? "opacity-40 cursor-not-allowed" : "hover:opacity-90"
              )}
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
            >
              {saving ? "Saving..." : "Finish →"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

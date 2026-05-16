"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Check, Loader2, ChevronLeft } from "lucide-react";
import { clsx } from "clsx";

const HEALTH_STEPS = [
  "TCP Reach",
  "Authentication",
  "Info Schema Read",
  "Sample SELECT",
  "Latency Probe",
  "Clock Skew",
];

const MOCK_TABLES = [
  "marketing_campaigns",
  "gigler_transactions",
  "gig_prices",
  "gig_vendor_stats",
];

type Step = 1 | 2 | 3;

interface WizardProps {
  engine: string;
  initialValues?: Record<string, string>;
  mode?: "create" | "edit";
}

export function Wizard({ engine }: WizardProps) {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);

  // Step 1 state
  const [projectId, setProjectId] = useState("");
  const [dataset, setDataset] = useState("");
  const [saJson, setSaJson] = useState("");

  // Step 2 state
  const [healthProgress, setHealthProgress] = useState(0);
  const [healthDone, setHealthDone] = useState(false);

  // Step 3 state
  const [selectedTables, setSelectedTables] = useState<Set<string>>(
    new Set(MOCK_TABLES)
  );

  const engineLabel =
    engine === "bigquery"
      ? "BigQuery"
      : engine === "postgres"
      ? "PostgreSQL"
      : engine === "mysql"
      ? "MySQL"
      : engine === "snowflake"
      ? "Snowflake"
      : engine;

  const runHealthCheck = useCallback(() => {
    setHealthProgress(0);
    setHealthDone(false);
    let i = 0;
    const tick = () => {
      if (i < HEALTH_STEPS.length) {
        i++;
        setHealthProgress(i);
        setTimeout(tick, 320);
      } else {
        setHealthDone(true);
      }
    };
    setTimeout(tick, 200);
  }, []);

  useEffect(() => {
    if (step === 2) {
      runHealthCheck();
    }
  }, [step, runHealthCheck]);

  function toggleTable(t: string) {
    setSelectedTables((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
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
                <span
                  className="t-small"
                  style={{ color: active ? "var(--fg-0)" : "var(--fg-2)" }}
                >
                  {label}
                </span>
              </div>
              {idx < 2 && (
                <div
                  className="mx-2"
                  style={{ width: 20, height: 1, background: "var(--line)" }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* ---- Step 1: Configure ---- */}
      {step === 1 && (
        <div className="space-y-4">
          <div>
            <label className="block t-small mb-1" style={{ color: "var(--fg-1)" }}>
              Engine
            </label>
            <div
              className="px-3 py-2 border border-line t-body"
              style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
            >
              {engineLabel}
            </div>
          </div>

          <div>
            <label className="block t-small mb-1" style={{ color: "var(--fg-1)" }}>
              GCP Project ID
            </label>
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="my-project-123"
              className="w-full px-3 py-2 border border-line t-body outline-none"
              style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
            />
          </div>

          <div>
            <label className="block t-small mb-1" style={{ color: "var(--fg-1)" }}>
              Dataset
            </label>
            <input
              type="text"
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}
              placeholder="Leave blank to scan all"
              className="w-full px-3 py-2 border border-line t-body outline-none"
              style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
            />
          </div>

          <div>
            <label className="block t-small mb-1" style={{ color: "var(--fg-1)" }}>
              Service Account JSON
            </label>
            <textarea
              value={saJson}
              onChange={(e) => setSaJson(e.target.value)}
              placeholder="Paste JSON key or upload file"
              rows={5}
              className="w-full px-3 py-2 border border-line t-small font-mono outline-none resize-none"
              style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
            />
          </div>

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
            {HEALTH_STEPS.map((label, i) => {
              const done = healthProgress > i;
              const active = healthProgress === i;
              return (
                <div key={label} className="flex items-center gap-3">
                  <div
                    className="w-5 h-5 flex items-center justify-center border"
                    style={{
                      borderColor: done ? "var(--pass)" : "var(--line)",
                      background: done ? "var(--pass)" : "var(--bg-2)",
                    }}
                  >
                    {done ? (
                      <Check size={11} strokeWidth={2.5} style={{ color: "var(--bg-0)" }} />
                    ) : active ? (
                      <Loader2 size={11} strokeWidth={2} className="animate-spin" style={{ color: "var(--fg-2)" }} />
                    ) : null}
                  </div>
                  <span
                    className="t-body"
                    style={{ color: done ? "var(--fg-0)" : "var(--fg-2)" }}
                  >
                    {label}
                  </span>
                </div>
              );
            })}
          </div>

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
              onClick={() => setStep(3)}
              disabled={!healthDone}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 t-small font-medium border transition-colors",
                healthDone ? "hover:opacity-90" : "opacity-40 cursor-not-allowed"
              )}
              style={{
                background: "var(--accent)",
                color: "var(--bg-0)",
                borderColor: "var(--accent)",
              }}
            >
              Configure Tables →
            </button>
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
            {MOCK_TABLES.map((t, i) => (
              <label
                key={t}
                className={clsx(
                  "flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors hover:bg-bg-2",
                  i > 0 && "border-t border-line"
                )}
              >
                <input
                  type="checkbox"
                  checked={selectedTables.has(t)}
                  onChange={() => toggleTable(t)}
                  className="accent-accent"
                  style={{ accentColor: "var(--accent)" }}
                />
                <span className="t-body font-mono" style={{ color: "var(--fg-0)" }}>
                  {t}
                </span>
              </label>
            ))}
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
              onClick={() => router.push("/sources")}
              className="flex items-center gap-2 px-4 py-2 t-small font-medium border hover:opacity-90"
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
            >
              Finish →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

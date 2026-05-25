"use client";

import { useState } from "react";
import { Pencil, X, Check } from "lucide-react";
import { ExpressionBuilder, ExpressionDef, emptyExpression } from "./expression-builder";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ADDITIVITY_LABELS: Record<string, string> = {
  full: "Full — sums across all dimensions including time",
  semi: "Semi — sums across dimensions but not time (use snapshot)",
  non: "Non — must be recomputed from numerator/denominator",
};

const DIRECTION_LABELS: Record<string, string> = {
  up: "↑ Up",
  down: "↓ Down",
  "in-band": "⇔ In-band",
};

const DIRECTION_COLORS: Record<string, string> = {
  up: "var(--pass)",
  down: "var(--fail)",
  "in-band": "var(--warn)",
};

const CADENCE_LABELS: Record<string, string> = {
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
};

interface Props {
  fqn: string;
  description: string;
  grain: string | null;
  additivity: string | null;
  good_direction: string | null;
  refresh_cadence: string | null;
  lineage: { label: string; kind?: string }[];
  source_id: string | null;
  expr_type: string | null;
  expr_sql: string | null;
  numerator_sql: string | null;
  denominator_sql: string | null;
  filter_sql: string | null;
}

export function MetricProfilePanel({
  fqn,
  description: initialDescription,
  grain: initialGrain,
  additivity: initialAdditivity,
  good_direction: initialDirection,
  refresh_cadence: initialCadence,
  lineage: initialLineage,
  source_id: initialSourceId,
  expr_type: initialExprType,
  expr_sql: initialExprSql,
  filter_sql: initialFilterSql,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [description, setDescription] = useState(initialDescription);
  const [grain, setGrain] = useState(initialGrain ?? "");
  const [additivity, setAdditivity] = useState(initialAdditivity ?? "");
  const [direction, setDirection] = useState(initialDirection ?? "");
  const [cadence, setCadence] = useState(initialCadence ?? "");
  const [lineage, setLineage] = useState<string[]>(
    initialLineage.length > 0 ? initialLineage.map((l) => l.label) : []
  );
  const [newStep, setNewStep] = useState("");
  const [expr, setExpr] = useState<ExpressionDef>(() => ({
    ...emptyExpression(),
    type: (initialExprType as ExpressionDef["type"]) ?? "simple",
    filterSql: initialFilterSql ?? "",
    customSql: initialExprSql ?? "",
    exprSql: initialExprSql ?? "",
  }));

  async function save() {
    setSaving(true);
    try {
      await fetch(`${API}/api/v1/metrics/${encodeURIComponent(fqn)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description,
          grain: grain || null,
          additivity: additivity || null,
          good_direction: direction || null,
          refresh_cadence: cadence || null,
          lineage: lineage.map((l) => ({ label: l })),
          expr_type: expr.type || null,
          expr_sql: expr.exprSql || null,
          filter_sql: expr.filterSql || null,
        }),
      });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  function cancel() {
    setDescription(initialDescription);
    setGrain(initialGrain ?? "");
    setAdditivity(initialAdditivity ?? "");
    setDirection(initialDirection ?? "");
    setCadence(initialCadence ?? "");
    setLineage(initialLineage.map((l) => l.label));
    setEditing(false);
  }

  function addLineageStep() {
    if (!newStep.trim()) return;
    setLineage((prev) => [...prev, newStep.trim()]);
    setNewStep("");
  }

  return (
    <div className="mb-6">
      {/* Badges row */}
      <div className="flex items-center gap-2 flex-wrap mb-2">
        {grain && (
          <span className="t-micro px-2 py-0.5 border border-line font-mono" style={{ color: "var(--fg-1)" }}>
            grain: {grain}
          </span>
        )}
        {additivity && (
          <span
            className="t-micro px-2 py-0.5 border border-line"
            style={{ color: "var(--fg-1)" }}
            title={ADDITIVITY_LABELS[additivity]}
          >
            {additivity} additive
          </span>
        )}
        {direction && (
          <span
            className="t-micro px-2 py-0.5 border"
            style={{ color: DIRECTION_COLORS[direction] ?? "var(--fg-1)", borderColor: DIRECTION_COLORS[direction] ?? "var(--line)" }}
          >
            {DIRECTION_LABELS[direction] ?? direction}
          </span>
        )}
        {cadence && (
          <span className="t-micro px-2 py-0.5 border border-line" style={{ color: "var(--fg-2)" }}>
            {CADENCE_LABELS[cadence] ?? cadence}
          </span>
        )}
        {!grain && !additivity && !direction && !cadence && !editing && (
          <span className="t-micro" style={{ color: "var(--fg-3)" }}>No profile — click Edit to add</span>
        )}
        <button
          onClick={() => setEditing(true)}
          className="flex items-center gap-1 t-micro px-2 py-0.5 border border-line transition-colors hover:opacity-80"
          style={{ color: "var(--fg-3)" }}
        >
          <Pencil size={10} strokeWidth={2} />
          Edit
        </button>
      </div>

      {/* Definition */}
      {description && !editing && (
        <p className="t-small mb-2" style={{ color: "var(--fg-2)", maxWidth: 640 }}>
          {description}
        </p>
      )}

      {/* Expression formula — view mode */}
      {initialExprSql && !editing && (
        <div className="mb-2">
          <p className="t-micro mb-1" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Expression</p>
          <code
            className="block t-micro font-mono px-2 py-1.5 border border-line overflow-x-auto"
            style={{ background: "var(--bg-0)", color: "var(--fg-1)" }}
          >
            SELECT {initialExprSql} FROM {fqn.split(".").at(-2) ?? "…"}
          </code>
        </div>
      )}

      {/* Lineage strip */}
      {lineage.length > 0 && !editing && (
        <div className="flex items-center gap-1 flex-wrap mb-1">
          <span className="t-micro" style={{ color: "var(--fg-3)" }}>Lineage:</span>
          {lineage.map((step, i) => (
            <span key={i} className="flex items-center gap-1">
              <span className="t-micro px-2 py-0.5 border border-line font-mono" style={{ color: "var(--fg-1)" }}>{step}</span>
              {i < lineage.length - 1 && <span style={{ color: "var(--fg-3)", fontSize: 10 }}>→</span>}
            </span>
          ))}
        </div>
      )}

      {/* Edit form */}
      {editing && (
        <div className="border border-line p-4 space-y-3 mt-2" style={{ background: "var(--bg-1)" }}>
          <div>
            <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Definition</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="One-sentence plain English definition"
              className="w-full px-2 py-1.5 t-small border border-line resize-none"
              style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
            />
          </div>
          <div className="grid grid-cols-4 gap-3">
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Grain</label>
              <input
                value={grain}
                onChange={(e) => setGrain(e.target.value)}
                placeholder="order, user, session…"
                className="w-full px-2 py-1.5 t-small border border-line"
                style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
              />
            </div>
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Additivity</label>
              <select
                value={additivity}
                onChange={(e) => setAdditivity(e.target.value)}
                className="w-full px-2 py-1.5 t-small border border-line"
                style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
              >
                <option value="">—</option>
                <option value="full">Full</option>
                <option value="semi">Semi</option>
                <option value="non">Non</option>
              </select>
            </div>
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Good direction</label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value)}
                className="w-full px-2 py-1.5 t-small border border-line"
                style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
              >
                <option value="">—</option>
                <option value="up">↑ Up</option>
                <option value="down">↓ Down</option>
                <option value="in-band">⇔ In-band</option>
              </select>
            </div>
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Cadence</label>
              <select
                value={cadence}
                onChange={(e) => setCadence(e.target.value)}
                className="w-full px-2 py-1.5 t-small border border-line"
                style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
              >
                <option value="">—</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
          </div>
          <div>
            <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Lineage steps</label>
            <div className="flex items-center gap-1 flex-wrap mb-2">
              {lineage.map((step, i) => (
                <span key={i} className="flex items-center gap-1">
                  <span className="t-micro px-2 py-0.5 border border-line font-mono flex items-center gap-1" style={{ color: "var(--fg-1)" }}>
                    {step}
                    <button onClick={() => setLineage((prev) => prev.filter((_, j) => j !== i))} className="hover:opacity-70">
                      <X size={9} style={{ color: "var(--fg-3)" }} />
                    </button>
                  </span>
                  {i < lineage.length - 1 && <span style={{ color: "var(--fg-3)", fontSize: 10 }}>→</span>}
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={newStep}
                onChange={(e) => setNewStep(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addLineageStep(); } }}
                placeholder="Add step (e.g. raw_orders, dbt_orders, this metric)"
                className="flex-1 px-2 py-1 t-small border border-line font-mono"
                style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
              />
              <button
                onClick={addLineageStep}
                className="px-2 py-1 t-micro border border-line hover:opacity-80"
                style={{ color: "var(--fg-2)" }}
              >
                Add
              </button>
            </div>
          </div>
          <div>
            <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Expression</label>
            <ExpressionBuilder
              dataset={fqn.split(".").at(-2) ?? ""}
              sourceId={initialSourceId}
              value={expr}
              onChange={setExpr}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={save}
              disabled={saving}
              className="flex items-center gap-1 px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
              style={{ color: "var(--accent)", borderColor: "var(--accent)" }}
            >
              <Check size={12} strokeWidth={2} />
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={cancel}
              className="px-3 py-1.5 t-small border border-line hover:opacity-80"
              style={{ color: "var(--fg-2)" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ExpressionDef {
  type: "simple" | "ratio" | "custom";
  agg: string;
  column: string;
  numeratorAgg: string;
  numeratorCol: string;
  denominatorAgg: string;
  denominatorCol: string;
  filterSql: string;
  customSql: string;
  exprSql: string;
}

export function emptyExpression(): ExpressionDef {
  return {
    type: "simple",
    agg: "sum",
    column: "",
    numeratorAgg: "sum",
    numeratorCol: "",
    denominatorAgg: "count",
    denominatorCol: "*",
    filterSql: "",
    customSql: "",
    exprSql: "",
  };
}

const AGGS = ["sum", "count", "count_distinct", "avg", "min", "max"] as const;

function buildSimpleExpr(agg: string, col: string, filter: string): string {
  if (!col && agg !== "count") return "";
  const c = col || "*";
  if (!filter) {
    if (agg === "count") return "COUNT(*)";
    if (agg === "count_distinct") return `COUNT(DISTINCT ${c})`;
    return `${agg.toUpperCase()}(${c})`;
  }
  if (agg === "count") return `COUNT(CASE WHEN ${filter} THEN 1 END)`;
  if (agg === "count_distinct") return `COUNT(DISTINCT CASE WHEN ${filter} THEN ${c} END)`;
  return `${agg.toUpperCase()}(CASE WHEN ${filter} THEN ${c} END)`;
}

function buildExprSql(def: ExpressionDef): string {
  if (def.type === "custom") return def.customSql.trim();
  if (def.type === "simple") return buildSimpleExpr(def.agg, def.column, def.filterSql);
  if (def.type === "ratio") {
    const num = buildSimpleExpr(def.numeratorAgg, def.numeratorCol, def.filterSql);
    const den = buildSimpleExpr(def.denominatorAgg, def.denominatorCol, def.filterSql);
    if (!num || !den) return "";
    return `(${num}) / NULLIF((${den}), 0)`;
  }
  return "";
}

interface Props {
  dataset: string;
  sourceId: string | null;
  value: ExpressionDef;
  onChange: (v: ExpressionDef) => void;
}

export function ExpressionBuilder({ dataset, sourceId, value, onChange }: Props) {
  const [columns, setColumns] = useState<string[]>([]);
  const [previewing, setPreviewing] = useState(false);
  const [previewResult, setPreviewResult] = useState<{ value: number | null; error: string | null } | null>(null);

  useEffect(() => {
    if (!dataset) return;
    fetch(`${API}/api/v1/datasets/${encodeURIComponent(dataset)}/columns`)
      .then((r) => (r.ok ? r.json() : []))
      .then((cols: { name: string }[]) => setColumns(cols.map((c) => c.name)))
      .catch(() => {});
  }, [dataset]);

  const update = useCallback(
    (patch: Partial<ExpressionDef>) => {
      const next = { ...value, ...patch };
      next.exprSql = buildExprSql(next);
      onChange(next);
      setPreviewResult(null);
    },
    [value, onChange]
  );

  async function preview() {
    const sql = buildExprSql(value);
    if (!sql || !dataset || !sourceId) return;
    setPreviewing(true);
    setPreviewResult(null);
    try {
      const res = await fetch(`${API}/api/v1/metrics/evaluate-expression`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset, source_id: sourceId, expr_sql: sql }),
      });
      setPreviewResult(await res.json());
    } catch {
      setPreviewResult({ value: null, error: "Network error" });
    } finally {
      setPreviewing(false);
    }
  }

  const generatedSql = buildExprSql(value);
  const canPreview = !!generatedSql && !!dataset && !!sourceId;

  const tabStyle = (active: boolean) => ({
    color: active ? "var(--accent)" : "var(--fg-2)",
    borderBottom: active ? "1px solid var(--accent)" : "1px solid transparent",
    background: "transparent",
  });

  const inputStyle = {
    background: "var(--bg-0)",
    color: "var(--fg-0)",
    outline: "none",
  } as const;

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      {/* Tabs */}
      <div className="flex border-b border-line">
        {(["simple", "ratio", "custom"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => update({ type: tab })}
            className="px-4 py-2 t-small capitalize"
            style={tabStyle(value.type === tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-3">
        {/* Simple mode */}
        {value.type === "simple" && (
          <div className="flex items-end gap-3 flex-wrap">
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Aggregation</label>
              <select
                value={value.agg}
                onChange={(e) => update({ agg: e.target.value })}
                className="px-2 py-1.5 t-small border border-line"
                style={inputStyle}
              >
                {AGGS.map((a) => (
                  <option key={a} value={a}>{a === "count_distinct" ? "COUNT DISTINCT" : a.toUpperCase()}</option>
                ))}
              </select>
            </div>
            {value.agg !== "count" && (
              <div>
                <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Column</label>
                <select
                  value={value.column}
                  onChange={(e) => update({ column: e.target.value })}
                  className="px-2 py-1.5 t-small border border-line font-mono"
                  style={{ ...inputStyle, minWidth: 160 }}
                >
                  <option value="">— pick column —</option>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            )}
            <div className="flex-1 min-w-48">
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Filter (WHERE)</label>
              <input
                value={value.filterSql}
                onChange={(e) => update({ filterSql: e.target.value })}
                placeholder="e.g. status = 'completed'"
                className="w-full px-2 py-1.5 t-small border border-line font-mono"
                style={inputStyle}
              />
            </div>
          </div>
        )}

        {/* Ratio mode */}
        {value.type === "ratio" && (
          <div className="space-y-3">
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)" }}>Numerator</p>
              <div className="flex items-center gap-3 flex-wrap">
                <select
                  value={value.numeratorAgg}
                  onChange={(e) => update({ numeratorAgg: e.target.value })}
                  className="px-2 py-1.5 t-small border border-line"
                  style={inputStyle}
                >
                  {AGGS.map((a) => (
                    <option key={a} value={a}>{a === "count_distinct" ? "COUNT DISTINCT" : a.toUpperCase()}</option>
                  ))}
                </select>
                {value.numeratorAgg !== "count" && (
                  <select
                    value={value.numeratorCol}
                    onChange={(e) => update({ numeratorCol: e.target.value })}
                    className="px-2 py-1.5 t-small border border-line font-mono"
                    style={{ ...inputStyle, minWidth: 160 }}
                  >
                    <option value="">— pick column —</option>
                    {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                )}
              </div>
            </div>
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)" }}>Denominator</p>
              <div className="flex items-center gap-3 flex-wrap">
                <select
                  value={value.denominatorAgg}
                  onChange={(e) => update({ denominatorAgg: e.target.value })}
                  className="px-2 py-1.5 t-small border border-line"
                  style={inputStyle}
                >
                  {AGGS.map((a) => (
                    <option key={a} value={a}>{a === "count_distinct" ? "COUNT DISTINCT" : a.toUpperCase()}</option>
                  ))}
                </select>
                {value.denominatorAgg !== "count" && (
                  <select
                    value={value.denominatorCol}
                    onChange={(e) => update({ denominatorCol: e.target.value })}
                    className="px-2 py-1.5 t-small border border-line font-mono"
                    style={{ ...inputStyle, minWidth: 160 }}
                  >
                    <option value="">— pick column —</option>
                    {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                )}
              </div>
            </div>
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Filter (applied to both numerator and denominator)</label>
              <input
                value={value.filterSql}
                onChange={(e) => update({ filterSql: e.target.value })}
                placeholder="e.g. status = 'completed'"
                className="w-full px-2 py-1.5 t-small border border-line font-mono"
                style={inputStyle}
              />
            </div>
          </div>
        )}

        {/* Custom SQL mode */}
        {value.type === "custom" && (
          <div>
            <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>
              SQL aggregate expression
            </label>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)" }}>
              Write any aggregate expression. This runs as: SELECT <em>your expression</em> FROM {dataset || "…"}
            </p>
            <textarea
              value={value.customSql}
              onChange={(e) => update({ customSql: e.target.value })}
              rows={3}
              placeholder="e.g. SUM(platform_fee_usd) / NULLIF(SUM(amount_usd), 0)"
              className="w-full px-2 py-1.5 t-small border border-line font-mono resize-none"
              style={inputStyle}
            />
          </div>
        )}

        {/* Generated SQL preview + run button */}
        {generatedSql && (
          <div className="flex items-start gap-3 pt-1">
            <div className="flex-1 min-w-0">
              <p className="t-micro mb-1" style={{ color: "var(--fg-3)" }}>Expression</p>
              <code
                className="block t-micro font-mono px-2 py-1.5 border border-line overflow-x-auto"
                style={{ background: "var(--bg-0)", color: "var(--fg-1)" }}
              >
                SELECT {generatedSql} FROM {dataset || "…"}
              </code>
            </div>
            {canPreview && (
              <div className="flex-shrink-0 pt-5">
                <button
                  onClick={preview}
                  disabled={previewing}
                  className="flex items-center gap-1.5 px-3 py-1.5 t-small border hover:opacity-80 disabled:opacity-40"
                  style={{ color: "var(--accent)", borderColor: "var(--accent)" }}
                >
                  {previewing ? <Loader2 size={11} strokeWidth={2} className="animate-spin" /> : "▶"}
                  Preview
                </button>
              </div>
            )}
          </div>
        )}

        {previewResult && (
          <div
            className="px-3 py-2 t-small font-mono border"
            style={{
              borderColor: previewResult.error ? "var(--fail)" : "var(--pass)",
              color: previewResult.error ? "var(--fail)" : "var(--fg-0)",
              background: previewResult.error ? "rgba(224,123,110,0.06)" : "rgba(100,200,120,0.06)",
            }}
          >
            {previewResult.error
              ? `Error: ${previewResult.error}`
              : `Result: ${previewResult.value != null ? previewResult.value.toLocaleString(undefined, { maximumFractionDigits: 6 }) : "null"}`
            }
          </div>
        )}
      </div>
    </div>
  );
}

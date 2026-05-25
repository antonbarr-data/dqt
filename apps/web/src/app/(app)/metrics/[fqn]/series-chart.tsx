"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface SeriesPoint {
  run_at: string;
  value: number;
  verdict: string;
}

function linearTrend(values: number[]): number[] {
  const n = values.length;
  if (n < 2) return values.map(() => 0);
  const meanX = (n - 1) / 2;
  const meanY = values.reduce((a, b) => a + b, 0) / n;
  const denom = values.reduce((s, _, i) => s + (i - meanX) ** 2, 0);
  if (denom === 0) return values.map(() => meanY);
  const slope = values.reduce((s, v, i) => s + (i - meanX) * (v - meanY), 0) / denom;
  const intercept = meanY - slope * meanX;
  return values.map((_, i) => slope * i + intercept);
}

function markOutliers(values: number[]): boolean[] {
  if (values.length < 3) return values.map(() => false);
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const std = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length);
  if (std === 0) return values.map(() => false);
  return values.map((v) => Math.abs(v - mean) / std > 2.0);
}

const DATE_RANGES = [
  { label: "7d", days: 7 },
  { label: "14d", days: 14 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

export function SeriesChart({ fqn }: { fqn: string }) {
  const [lookback, setLookback] = useState(30);
  const [data, setData] = useState<SeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/v1/metrics/${encodeURIComponent(fqn)}/series?lookback_days=${lookback}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((d: SeriesPoint[]) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [fqn, lookback]);

  const header = (
    <div className="flex items-center justify-between mb-2">
      <p className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        Time series
      </p>
      <div className="flex items-center gap-1">
        {DATE_RANGES.map((r) => (
          <button
            key={r.label}
            onClick={() => setLookback(r.days)}
            className="t-micro px-1.5 py-0.5 border"
            style={{
              borderColor: lookback === r.days ? "var(--accent)" : "var(--line)",
              color: lookback === r.days ? "var(--accent)" : "var(--fg-3)",
              background: lookback === r.days ? "var(--accent-bg)" : "transparent",
            }}
          >
            {r.label}
          </button>
        ))}
      </div>
    </div>
  );

  if (loading)
    return (
      <div className="mb-6">
        {header}
        <div className="h-40 flex items-center justify-center border border-line" style={{ background: "var(--bg-1)" }}>
          <span className="t-micro" style={{ color: "var(--fg-3)" }}>Loading series...</span>
        </div>
      </div>
    );

  if (!data.length)
    return (
      <div className="mb-6">
        {header}
        <div className="h-40 flex items-center justify-center border border-line" style={{ background: "var(--bg-1)" }}>
          <span className="t-micro" style={{ color: "var(--fg-3)" }}>No time series data available</span>
        </div>
      </div>
    );

  const values = data.map((p) => p.value);
  const trend = linearTrend(values);
  const outlierFlags = markOutliers(values);

  const chartData = data.map((p, i) => ({
    date: new Date(p.run_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: p.value,
    trend: Math.round(trend[i] * 10000) / 10000,
    outlier: outlierFlags[i] ? p.value : undefined,
  }));

  return (
    <div className="mb-6">
      {header}
      <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
            <XAxis
              dataKey="date"
              tick={{ fill: "var(--fg-3)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "var(--fg-3)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip
              contentStyle={{
                background: "var(--bg-2)",
                border: "1px solid var(--line)",
                borderRadius: 0,
                fontSize: 11,
                fontFamily: "var(--font-jetbrains-mono)",
              }}
              labelStyle={{ color: "var(--fg-2)" }}
              itemStyle={{ color: "var(--accent)" }}
            />
            <Line dataKey="value" stroke="var(--accent)" strokeWidth={1.5} dot={false} name="value" />
            <Line
              dataKey="trend"
              stroke="#d9b566"
              strokeWidth={1}
              strokeDasharray="4 4"
              dot={false}
              activeDot={false}
              name="trend"
            />
            <Line
              dataKey="outlier"
              stroke="none"
              strokeWidth={0}
              dot={{ r: 4, fill: "var(--fail)", stroke: "var(--fail)" }}
              activeDot={false}
              isAnimationActive={false}
              name="outlier"
            />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-4 mt-1">
          <span className="t-micro flex items-center gap-1.5" style={{ color: "var(--fg-3)" }}>
            <span style={{ display: "inline-block", width: 16, borderTop: "1.5px solid var(--accent)" }} />
            value
          </span>
          <span className="t-micro flex items-center gap-1.5" style={{ color: "var(--fg-3)" }}>
            <span style={{ display: "inline-block", width: 16, borderTop: "1px dashed #d9b566" }} />
            trend
          </span>
          <span className="t-micro flex items-center gap-1.5" style={{ color: "var(--fg-3)" }}>
            <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "var(--fail)" }} />
            outlier
          </span>
        </div>
      </div>
    </div>
  );
}

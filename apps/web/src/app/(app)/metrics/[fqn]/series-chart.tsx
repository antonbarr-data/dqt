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

export function SeriesChart({ fqn }: { fqn: string }) {
  const [data, setData] = useState<SeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/v1/metrics/${encodeURIComponent(fqn)}/series?lookback_days=30`)
      .then((r) => (r.ok ? r.json() : []))
      .then((d: SeriesPoint[]) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [fqn]);

  if (loading)
    return (
      <div
        className="h-32 flex items-center justify-center border border-line mb-6"
        style={{ background: "var(--bg-1)" }}
      >
        <span className="t-micro" style={{ color: "var(--fg-3)" }}>
          Loading series...
        </span>
      </div>
    );

  if (!data.length)
    return (
      <div
        className="h-32 flex items-center justify-center border border-line mb-6"
        style={{ background: "var(--bg-1)" }}
      >
        <span className="t-micro" style={{ color: "var(--fg-3)" }}>
          No time series data available
        </span>
      </div>
    );

  const chartData = data.map((p) => ({
    date: new Date(p.run_at).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    value: p.value,
    verdict: p.verdict,
  }));

  return (
    <div className="mb-6">
      <p
        className="t-micro mb-2"
        style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
      >
        Time series (30d)
      </p>
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
            <Line dataKey="value" stroke="var(--accent)" strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

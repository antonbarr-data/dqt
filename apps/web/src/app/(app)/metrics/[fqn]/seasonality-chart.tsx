"use client";

import { BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer } from "recharts";

interface Props {
  data: { day: string; avg: number }[];
  mean: number;
}

export function SeasonalityChart({ data, mean }: Props) {
  return (
    <div>
      <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        Seasonality — day of week
      </p>
      <div style={{ height: 80 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barCategoryGap="20%">
            <XAxis
              dataKey="day"
              tick={{ fontSize: 9, fill: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis hide domain={["auto", "auto"]} />
            <Tooltip
              formatter={(v) => [Number(v).toFixed(4), "avg"]}
              contentStyle={{
                background: "var(--bg-1)",
                border: "1px solid var(--line)",
                borderRadius: 0,
                fontSize: 11,
                fontFamily: "var(--font-jetbrains-mono)",
              }}
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
            />
            <Bar dataKey="avg" radius={0}>
              {data.map((entry) => (
                <Cell
                  key={entry.day}
                  fill={entry.avg >= mean ? "var(--accent)" : "var(--fg-3)"}
                  opacity={0.7}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="t-micro mt-1" style={{ color: "var(--fg-3)" }}>
        bars above mean highlighted
      </p>
    </div>
  );
}

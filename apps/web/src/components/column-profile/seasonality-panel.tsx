"use client";

import { useMemo } from "react";

interface RunPoint {
  id: number;
  detector: string;
  score: number | null;
  verdict: string | null;
  ran_at: string;
}

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const HOUR_LABELS = ["0h", "6h", "12h", "18h", "24h"];

function colorForScore(score: number, max: number): string {
  if (max === 0) return "var(--bg-2)";
  const intensity = score / max;
  if (intensity < 0.33) return "rgba(127,179,148,0.15)";
  if (intensity < 0.66) return "rgba(217,181,102,0.25)";
  return "rgba(217,100,100,0.35)";
}

export function SeasonalityPanel({ history }: { history: RunPoint[] }) {
  const { byDow, byHour, hasSufficientData } = useMemo(() => {
    const valid = history.filter(r => r.score !== null);
    if (valid.length < 7) {
      return { byDow: [], byHour: [], hasSufficientData: false };
    }

    // Average score by day-of-week (0=Sun..6=Sat)
    const dowBuckets: number[][] = Array.from({ length: 7 }, () => []);
    const hourBuckets: number[][] = Array.from({ length: 24 }, () => []);
    for (const r of valid) {
      const d = new Date(r.ran_at);
      dowBuckets[d.getDay()].push(r.score!);
      hourBuckets[d.getHours()].push(r.score!);
    }

    const avg = (arr: number[]) => arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0;
    const byDow = dowBuckets.map(arr => avg(arr));
    const byHour = hourBuckets.map(arr => avg(arr));

    return { byDow, byHour, hasSufficientData: true };
  }, [history]);

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Seasonality
        </span>
      </div>

      {!hasSufficientData ? (
        <div className="px-4 py-6 t-small flex items-center justify-center" style={{ color: "var(--fg-3)" }}>
          Not enough runs to detect seasonality (need 7+)
        </div>
      ) : (
        <div className="px-4 py-4 flex flex-col gap-4">
          {/* Day-of-week heatmap */}
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Avg score by day of week
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 3 }}>
              {byDow.map((score, i) => {
                const max = Math.max(...byDow);
                return (
                  <div key={i} className="flex flex-col items-center gap-1">
                    <div style={{
                      height: 32, width: "100%",
                      background: colorForScore(score, max),
                      border: "1px solid var(--line)",
                    }} title={`${DAY_NAMES[i]}: ${(score * 100).toFixed(1)}%`} />
                    <span className="t-micro" style={{ color: "var(--fg-3)" }}>{DAY_NAMES[i]}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Hour-of-day heatmap (condensed: 6-hour buckets) */}
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Avg score by hour of day
            </p>
            {/* Group into 6-hour buckets for display */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 3 }}>
              {[0, 1, 2, 3].map(bucket => {
                const hours = byHour.slice(bucket * 6, bucket * 6 + 6);
                const avg = hours.reduce((s, v) => s + v, 0) / Math.max(hours.length, 1);
                const max = Math.max(...byHour);
                return (
                  <div key={bucket} className="flex flex-col items-center gap-1">
                    <div style={{
                      height: 32, width: "100%",
                      background: colorForScore(avg, max),
                      border: "1px solid var(--line)",
                    }} title={`${bucket * 6}h-${bucket * 6 + 6}h: ${(avg * 100).toFixed(1)}%`} />
                    <span className="t-micro" style={{ color: "var(--fg-3)" }}>
                      {HOUR_LABELS[bucket]}-{HOUR_LABELS[bucket + 1]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

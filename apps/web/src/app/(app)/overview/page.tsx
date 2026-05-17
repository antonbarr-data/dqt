"use client";

import { useEffect, useState, useCallback } from "react";
import { FeedItemCard } from "@/components/feed/feed-item-card";

interface FeedItem {
  item_id: string;
  metric_fqn: string;
  display_name: string;
  observed_change: number;
  significance: number;
  primary_channel: "data" | "business" | "mixed";
  summary_paragraph: string;
  estimated_data_contribution: [number, number];
  estimated_business_contribution: [number, number];
  evidence_chips: { label: string; display_value: string; direction: "up" | "down" | "flat" }[];
  reviewed: boolean;
}

type ChannelFilter = "all" | "data" | "business" | "mixed";

export default function OverviewPage() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ChannelFilter>("all");
  const [lookback, setLookback] = useState("24h");

  const loadFeed = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/v1/feed/today?lookback=${lookback}&limit=20`);
      if (resp.ok) setItems(await resp.json());
      else setError("Failed to load feed.");
    } catch {
      setError("Failed to load feed.");
    } finally {
      setLoading(false);
    }
  }, [lookback]);

  useEffect(() => { loadFeed(); }, [loadFeed]);

  const markReviewed = useCallback(async (itemId: string) => {
    await fetch(`/api/v1/feed/items/${itemId}/reviewed`, { method: "POST" });
    setItems(prev => prev.filter(i => i.item_id !== itemId));
  }, []);

  const visible = filter === "all" ? items : items.filter(i => i.primary_channel === filter);

  return (
    <div className="p-6">
      <div className="flex items-baseline justify-between mb-6">
        <div>
          <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Today</h1>
          <p className="t-small mt-1" style={{ color: "var(--fg-3)" }}>
            Significant metric movements in the last {lookback}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={lookback}
            onChange={e => setLookback(e.target.value)}
            className="t-small border border-line px-2 py-1"
            style={{ background: "var(--bg-1)", color: "var(--fg-1)" }}
          >
            <option value="24h">Last 24h</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
          <button
            onClick={loadFeed}
            className="t-small px-3 py-1 border border-line hover:border-accent transition-colors"
            style={{ color: "var(--fg-1)", background: "var(--bg-1)" }}
          >
            Refresh
          </button>
        </div>
      </div>
      <div className="flex gap-2 mb-6">
        {(["all", "data", "business", "mixed"] as ChannelFilter[]).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="t-micro px-2 py-1 border transition-colors"
            style={{
              borderColor: filter === f ? "var(--accent)" : "var(--line)",
              color: filter === f ? "var(--accent)" : "var(--fg-2)",
              background: filter === f ? "var(--accent-bg)" : "var(--bg-1)",
              letterSpacing: "0.06em",
            }}
          >
            {f === "all" ? "All" : f === "data" ? "Data issues" : f === "business" ? "Business shifts" : "Mixed"}
          </button>
        ))}
      </div>
      {error && (
        <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
          <p className="t-small" style={{ color: "var(--fail)" }}>{error}</p>
        </div>
      )}
      {!error && loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="border border-line p-4 h-32 animate-pulse"
                 style={{ background: "var(--bg-1)" }} />
          ))}
        </div>
      ) : !error && visible.length === 0 ? (
        <div className="border border-line p-12 text-center" style={{ background: "var(--bg-1)" }}>
          <p className="t-small" style={{ color: "var(--fg-3)" }}>
            No significant movements in the last {lookback}.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map(item => (
            <FeedItemCard
              key={item.item_id}
              {...item}
              onMarkReviewed={markReviewed}
            />
          ))}
        </div>
      )}
    </div>
  );
}

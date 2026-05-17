"use client";

import Link from "next/link";

interface EvidenceChip {
  label: string;
  display_value: string;
  direction: "up" | "down" | "flat";
}

interface FeedItemProps {
  item_id: string;
  metric_fqn: string;
  display_name: string;
  observed_change: number;
  primary_channel: "data" | "business" | "mixed";
  summary_paragraph: string;
  evidence_chips: EvidenceChip[];
  onMarkReviewed: (itemId: string) => void;
}

function ChannelTag({ channel }: { channel: string }) {
  const label = channel === "data" ? "data issue" : channel === "business" ? "business shift" : "mixed";
  const color = channel === "data" ? "var(--fail)" : channel === "business" ? "var(--pass)" : "var(--warn)";
  return (
    <span className="t-micro font-mono px-1.5 py-0.5 border"
          style={{ color, borderColor: color, background: `${color}12`, letterSpacing: "0.06em" }}>
      {label}
    </span>
  );
}

export function FeedItemCard({
  item_id, metric_fqn, display_name, observed_change,
  primary_channel, summary_paragraph, evidence_chips, onMarkReviewed,
}: FeedItemProps) {
  const pct = Math.abs(observed_change * 100).toFixed(1);
  const direction = observed_change < 0 ? "down" : "up";
  const changeColor = direction === "down" ? "var(--fail)" : "var(--pass)";

  return (
    <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>{display_name}</span>
          <ChannelTag channel={primary_channel} />
        </div>
        <span className="t-small font-mono font-medium" style={{ color: changeColor }}>
          {direction === "down" ? "-" : "+"}{pct}%
        </span>
      </div>
      <p className="t-small mb-3" style={{ color: "var(--fg-1)", lineHeight: 1.6 }}>
        {summary_paragraph}
      </p>
      {evidence_chips.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {evidence_chips.map((chip, i) => (
            <div key={i} className="flex items-center gap-1 border border-line px-2 py-1"
                 style={{ background: "var(--bg-2)" }}>
              <span className="t-micro font-mono" style={{ color: "var(--fg-2)" }}>{chip.label}</span>
              <span className="t-micro" style={{ color: "var(--fg-1)" }}>{chip.display_value}</span>
            </div>
          ))}
        </div>
      )}
      <div className="flex items-center gap-4">
        <Link href={`/metrics/${encodeURIComponent(metric_fqn)}`}
              className="t-small hover:underline"
              style={{ color: "var(--accent)" }}>
          Dig deeper
        </Link>
        <button
          className="t-small hover:opacity-70"
          style={{ color: "var(--fg-3)" }}
          onClick={() => onMarkReviewed(item_id)}
        >
          Mark reviewed
        </button>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";

interface EditModalProps {
  sub: {
    id: string;
    cadence: string;
    delivery_channels: string[];
    significance_threshold: number | null;
  };
  onClose: () => void;
  onSave: (data: {
    cadence: string;
    delivery_channels: string[];
    significance_threshold: number | null;
  }) => Promise<void>;
}

export function EditModal({ sub, onClose, onSave }: EditModalProps) {
  const [cadence, setCadence] = useState(sub.cadence);
  const [channels, setChannels] = useState<string[]>(sub.delivery_channels);
  const [threshold, setThreshold] = useState(
    sub.significance_threshold != null
      ? (sub.significance_threshold * 100).toFixed(0)
      : ""
  );
  const [saving, setSaving] = useState(false);

  function toggleChannel(ch: string) {
    setChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  }

  async function handleSave() {
    setSaving(true);
    await onSave({
      cadence,
      delivery_channels: channels,
      significance_threshold: threshold ? parseFloat(threshold) / 100 : null,
    });
    setSaving(false);
  }

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ background: "rgba(0,0,0,0.4)" }}
        onClick={onClose}
      />
      <div
        className="fixed top-1/2 left-1/2 z-50"
        style={{
          width: 400,
          background: "var(--bg-1)",
          border: "1px solid var(--line)",
          padding: 24,
          transform: "translate(-50%, -50%)",
        }}
      >
        <h2 className="t-small font-medium mb-5" style={{ color: "var(--fg-0)" }}>
          Edit subscription
        </h2>

        <div className="mb-4">
          <label
            className="t-micro mb-1.5 block"
            style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
          >
            Cadence
          </label>
          <select
            value={cadence}
            onChange={(e) => setCadence(e.target.value)}
            className="w-full t-small px-3 py-2 border border-line"
            style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
          >
            <option value="daily">Daily digest</option>
            <option value="weekly">Weekly digest</option>
            <option value="on_threshold">On threshold</option>
          </select>
        </div>

        <div className="mb-4">
          <label
            className="t-micro mb-1.5 block"
            style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
          >
            Channels
          </label>
          <div className="flex gap-3">
            {(["email", "slack"] as const).map((ch) => (
              <button
                key={ch}
                onClick={() => toggleChannel(ch)}
                className="t-small px-3 py-1.5 border"
                style={{
                  borderColor: channels.includes(ch) ? "var(--accent)" : "var(--line)",
                  color: channels.includes(ch) ? "var(--accent)" : "var(--fg-2)",
                  background: channels.includes(ch) ? "var(--accent-bg)" : "var(--bg-2)",
                }}
              >
                {ch}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-6">
          <label
            className="t-micro mb-1.5 block"
            style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
          >
            Alert threshold (%) -- blank = auto (2 sigma)
          </label>
          <input
            type="number"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            placeholder="Auto"
            className="w-full t-small px-3 py-2 border border-line"
            style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
          />
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="t-small px-4 py-2 border border-line hover:opacity-70"
            style={{ color: "var(--fg-2)" }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="t-small px-4 py-2 hover:opacity-80 disabled:opacity-40"
            style={{ background: "var(--accent)", color: "#0a0a0a" }}
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </>
  );
}

"use client";

import { useState } from "react";
import { Pencil, X, Check } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  fqn: string;
  description: string;
  lineage: { label: string; kind?: string }[];
}

export function MetricProfilePanel({
  fqn,
  description: initialDescription,
  lineage,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [description, setDescription] = useState(initialDescription);

  async function save() {
    setSaving(true);
    try {
      await fetch(`${API}/api/v1/metrics/${encodeURIComponent(fqn)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description }),
      });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  function cancel() {
    setDescription(initialDescription);
    setEditing(false);
  }

  return (
    <div className="mb-6">
      {/* Description */}
      {editing ? (
        <div className="border border-line p-4 space-y-3 mt-2" style={{ background: "var(--bg-1)" }}>
          <div>
            <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Definition</label>
            <textarea
              autoFocus
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="One-sentence plain English definition"
              className="w-full px-2 py-1.5 t-small border border-line resize-none"
              style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
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
      ) : (
        <div className="flex items-start gap-2 mb-2">
          {description ? (
            <p className="t-small flex-1" style={{ color: "var(--fg-2)", maxWidth: 640 }}>
              {description}
            </p>
          ) : (
            <p className="t-small flex-1" style={{ color: "var(--fg-3)" }}>No description</p>
          )}
          <button
            onClick={() => setEditing(true)}
            className="flex items-center gap-1 t-micro px-2 py-0.5 border border-line transition-colors hover:opacity-80 flex-shrink-0"
            style={{ color: "var(--fg-3)" }}
          >
            <Pencil size={10} strokeWidth={2} />
            Edit
          </button>
        </div>
      )}

      {/* Lineage strip — read-only */}
      {lineage.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap mb-1">
          <span className="t-micro" style={{ color: "var(--fg-3)" }}>Lineage:</span>
          {lineage.map((step, i) => (
            <span key={i} className="flex items-center gap-1">
              <span className="t-micro px-2 py-0.5 border border-line font-mono" style={{ color: "var(--fg-1)" }}>{step.label}</span>
              {i < lineage.length - 1 && <span style={{ color: "var(--fg-3)", fontSize: 10 }}>→</span>}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

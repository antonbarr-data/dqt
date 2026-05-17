"use client";

import { useState, useEffect } from "react";
import { Bell, Edit2, Trash2, Eye } from "lucide-react";
import { EditModal } from "@/components/subscriptions/edit-modal";

interface Subscription {
  id: string;
  user_id: string;
  metric_fqns: string[];
  cadence: "daily" | "weekly" | "on_threshold";
  delivery_channels: string[];
  significance_threshold: number | null;
  schedule_time: string;
  created_at: string;
}

interface DigestHistory {
  cadence: string;
  generated_at: string;
  data_issues_count: number;
  real_shifts_count: number;
  no_significant_change_count: number;
  plain_text: string;
}

const CADENCE_LABEL: Record<string, string> = {
  daily: "Daily digest",
  weekly: "Weekly digest",
  on_threshold: "On threshold",
};

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [editSub, setEditSub] = useState<Subscription | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<{ plain_text: string } | null>(null);
  const [history, setHistory] = useState<DigestHistory[]>([]);
  const [selectedHistory, setSelectedHistory] = useState<DigestHistory | null>(null);

  useEffect(() => {
    fetch("/api/v1/subscriptions?user_id=demo")
      .then((r) => r.json())
      .then((data) => {
        setSubs(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));

    fetch("/api/v1/trigger/history")
      .then((r) => r.json())
      .then(setHistory)
      .catch(() => {});
  }, []);

  async function handleDelete(id: string) {
    await fetch(`/api/v1/subscriptions/${id}`, { method: "DELETE" });
    setSubs((prev) => prev.filter((s) => s.id !== id));
  }

  async function handlePreview(id: string) {
    setPreviewId(id);
    setSelectedHistory(null);
    setPreviewData(null);
    const resp = await fetch(`/api/v1/subscriptions/${id}/preview`);
    const data = await resp.json();
    setPreviewData(data);
  }

  function closeSidePanel() {
    setPreviewId(null);
    setPreviewData(null);
    setSelectedHistory(null);
  }

  const showPanel = previewId !== null || selectedHistory !== null;

  return (
    <div className="flex h-full">
      {/* Main content */}
      <div className="flex-1 p-6 overflow-y-auto min-w-0">
        {/* Page header */}
        <div className="flex items-center gap-3 mb-6">
          <Bell size={18} strokeWidth={1.6} style={{ color: "var(--fg-2)" }} />
          <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Subscriptions</h1>
        </div>

        {/* Subscription list */}
        {loading ? (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-20 border border-line"
                style={{ background: "var(--bg-2)", opacity: 0.5 }}
              />
            ))}
          </div>
        ) : subs.length === 0 ? (
          <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
            <p className="t-small" style={{ color: "var(--fg-3)" }}>
              No subscriptions yet. Use the Subscribe button on any metric page or feed item.
            </p>
          </div>
        ) : (
          <div className="space-y-2 mb-8">
            {subs.map((sub) => (
              <div
                key={sub.id}
                className="border border-line p-4"
                style={{ background: "var(--bg-1)" }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>
                        {CADENCE_LABEL[sub.cadence] ?? sub.cadence}
                      </span>
                      {sub.delivery_channels.map((ch) => (
                        <span
                          key={ch}
                          className="t-micro font-mono px-1.5 py-0.5 border border-line"
                          style={{ color: "var(--fg-2)" }}
                        >
                          {ch}
                        </span>
                      ))}
                      {sub.significance_threshold != null && (
                        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
                          threshold: {(sub.significance_threshold * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {sub.metric_fqns.map((fqn) => (
                        <span
                          key={fqn}
                          className="t-micro font-mono px-1.5 py-0.5"
                          style={{ background: "var(--bg-2)", color: "var(--accent)" }}
                        >
                          {fqn}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <button
                      onClick={() => handlePreview(sub.id)}
                      className="t-small hover:opacity-70"
                      style={{ color: "var(--fg-2)" }}
                      title="Preview next digest"
                    >
                      <Eye size={14} strokeWidth={1.6} />
                    </button>
                    <button
                      onClick={() => setEditSub(sub)}
                      className="t-small hover:opacity-70"
                      style={{ color: "var(--fg-2)" }}
                      title="Edit subscription"
                    >
                      <Edit2 size={14} strokeWidth={1.6} />
                    </button>
                    <button
                      onClick={() => handleDelete(sub.id)}
                      className="t-small hover:opacity-70"
                      style={{ color: "var(--fail)" }}
                      title="Cancel subscription"
                    >
                      <Trash2 size={14} strokeWidth={1.6} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Digest history */}
        {history.length > 0 && (
          <div>
            <p
              className="t-micro mb-3"
              style={{ color: "var(--fg-3)", letterSpacing: "0.10em", textTransform: "uppercase" }}
            >
              Digest history
            </p>
            <div className="space-y-1">
              {history.map((h, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setSelectedHistory(selectedHistory === h ? null : h);
                    setPreviewId(null);
                    setPreviewData(null);
                  }}
                  className="w-full text-left border border-line p-3 hover:bg-bg-2 transition-colors"
                  style={{
                    background: selectedHistory === h ? "var(--bg-2)" : "var(--bg-1)",
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="t-small" style={{ color: "var(--fg-1)" }}>
                      {h.cadence.charAt(0).toUpperCase() + h.cadence.slice(1)} digest
                    </span>
                    <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
                      {new Date(h.generated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex gap-3 mt-1">
                    {h.data_issues_count > 0 && (
                      <span className="t-micro" style={{ color: "var(--fail)" }}>
                        {h.data_issues_count} data issues
                      </span>
                    )}
                    {h.real_shifts_count > 0 && (
                      <span className="t-micro" style={{ color: "var(--pass)" }}>
                        {h.real_shifts_count} shifts
                      </span>
                    )}
                    {h.no_significant_change_count > 0 && (
                      <span className="t-micro" style={{ color: "var(--fg-3)" }}>
                        {h.no_significant_change_count} unchanged
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Side panel -- preview or history detail */}
      {showPanel && (
        <div
          className="border-l border-line overflow-y-auto p-5 flex-shrink-0"
          style={{ width: 380, background: "var(--bg-1)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>
              {selectedHistory ? "Digest" : "Next digest preview"}
            </span>
            <button
              onClick={closeSidePanel}
              className="t-small hover:opacity-70"
              style={{ color: "var(--fg-3)" }}
            >
              x
            </button>
          </div>
          {selectedHistory ? (
            <pre
              className="t-micro whitespace-pre-wrap"
              style={{ color: "var(--fg-1)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {selectedHistory.plain_text}
            </pre>
          ) : previewData ? (
            <pre
              className="t-micro whitespace-pre-wrap"
              style={{ color: "var(--fg-1)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {previewData.plain_text}
            </pre>
          ) : (
            <div
              className="h-32 border border-line"
              style={{ background: "var(--bg-2)", opacity: 0.5 }}
            />
          )}
        </div>
      )}

      {/* Edit modal */}
      {editSub && (
        <EditModal
          sub={editSub}
          onClose={() => setEditSub(null)}
          onSave={async (updated) => {
            const resp = await fetch(`/api/v1/subscriptions/${editSub.id}`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(updated),
            });
            const data = await resp.json();
            setSubs((prev) => prev.map((s) => (s.id === data.id ? data : s)));
            setEditSub(null);
          }}
        />
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Phone, RefreshCw } from "lucide-react";
import { authHeaders } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

interface ShiftEntry {
  user_id: string;
  email: string;
  days_of_week: number[];
}

interface OncallStatus {
  current_oncall: (ShiftEntry & { today: string }) | null;
  upcoming_oncall: (ShiftEntry & { next_day: string; days_until: number }) | null;
  schedule: ShiftEntry[];
  today_name: string;
}

export default function OncallPage() {
  const [status, setStatus] = useState<OncallStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [redistributing, setRedistributing] = useState(false);
  const [editDays, setEditDays] = useState<Record<string, number[]>>({});
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => { fetchStatus(); }, []);

  async function fetchStatus() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/oncall/status`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to load on-call status");
      const data: OncallStatus = await res.json();
      setStatus(data);
      const initial: Record<string, number[]> = {};
      for (const s of data.schedule) initial[s.user_id] = [...s.days_of_week];
      setEditDays(initial);
    } finally {
      setLoading(false);
    }
  }

  async function redistribute() {
    setRedistributing(true);
    try {
      await fetch(`${API}/api/v1/oncall/redistribute`, { method: "POST", headers: authHeaders() });
      await fetchStatus();
    } finally {
      setRedistributing(false);
    }
  }

  async function saveShift(userId: string) {
    setSaving(userId);
    try {
      await fetch(`${API}/api/v1/oncall/shifts/${userId}`, {
        method: "PUT",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ days_of_week: editDays[userId] ?? [] }),
      });
      await fetchStatus();
    } finally {
      setSaving(null);
    }
  }

  function toggleDay(userId: string, day: number) {
    setEditDays((prev) => {
      const current = prev[userId] ?? [];
      const next = current.includes(day) ? current.filter((d) => d !== day) : [...current, day];
      return { ...prev, [userId]: next };
    });
  }

  function daysChanged(userId: string): boolean {
    const orig = status?.schedule.find((s) => s.user_id === userId)?.days_of_week ?? [];
    const current = editDays[userId] ?? [];
    return JSON.stringify([...orig].sort()) !== JSON.stringify([...current].sort());
  }

  if (loading) {
    return (
      <div className="p-6">
        <p className="t-small" style={{ color: "var(--fg-2)" }}>Loading...</p>
      </div>
    );
  }

  if (!status) return null;

  // Build coverage map: day -> email
  const coverage: Record<number, string> = {};
  for (const s of status.schedule) {
    for (const d of s.days_of_week) coverage[d] = s.email;
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Phone size={14} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
          <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>On-Call Schedule</h1>
        </div>
        <button
          onClick={redistribute}
          disabled={redistributing}
          className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:opacity-80 disabled:opacity-40"
          style={{ color: "var(--fg-2)" }}
          title="Evenly redistribute all 7 days among eligible users"
        >
          <RefreshCw size={12} strokeWidth={2} className={redistributing ? "animate-spin" : ""} />
          Auto-distribute
        </button>
      </div>

      {/* Current on-call banner */}
      {status.current_oncall ? (
        <div
          className="border p-4 flex items-start gap-3"
          style={{ borderColor: "var(--accent)", background: "rgba(99,102,241,0.06)" }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--pass)",
              marginTop: 5,
              flexShrink: 0,
            }}
          />
          <div>
            <p className="t-micro mb-0.5" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>On-call now — {status.today_name}</p>
            <p className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{status.current_oncall.email}</p>
          </div>
        </div>
      ) : (
        <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
          <p className="t-micro mb-1" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>No one on call today ({status.today_name})</p>
          {status.upcoming_oncall && (
            <p className="t-small" style={{ color: "var(--fg-2)" }}>
              Next: <span className="font-mono" style={{ color: "var(--fg-0)" }}>{status.upcoming_oncall.email}</span>
              {" "}<span style={{ color: "var(--fg-3)" }}>on {status.upcoming_oncall.next_day} ({status.upcoming_oncall.days_until}d)</span>
            </p>
          )}
        </div>
      )}

      {/* Weekly grid */}
      <div>
        <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>This week</p>
        <div className="grid grid-cols-7 gap-px" style={{ background: "var(--line)" }}>
          {DAY_NAMES.map((name, d) => {
            const covered = coverage[d];
            const isToday = name === status.today_name;
            return (
              <div
                key={d}
                className="px-2 py-3 text-center"
                style={{
                  background: isToday ? "rgba(99,102,241,0.08)" : "var(--bg-1)",
                  borderBottom: isToday ? "2px solid var(--accent)" : undefined,
                }}
              >
                <p className="t-micro mb-1.5" style={{ color: isToday ? "var(--accent)" : "var(--fg-3)", letterSpacing: "0.06em" }}>
                  {name.slice(0, 3).toUpperCase()}
                </p>
                <p
                  className="t-micro font-mono"
                  style={{ color: covered ? "var(--fg-0)" : "var(--fg-3)", wordBreak: "break-all" }}
                  title={covered ?? "uncovered"}
                >
                  {covered ? covered.split("@")[0] : <span style={{ color: "var(--fail)" }}>--</span>}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Rotation members */}
      {status.schedule.length === 0 ? (
        <div className="border border-line p-6 text-center" style={{ background: "var(--bg-1)" }}>
          <p className="t-small" style={{ color: "var(--fg-3)" }}>
            No users are marked as on-call eligible yet. Go to{" "}
            <a href="/settings/users" style={{ color: "var(--accent)" }}>User Management</a>{" "}
            to add users to the rotation.
          </p>
        </div>
      ) : (
        <div>
          <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Rotation members</p>
          <div className="border border-line divide-y divide-line" style={{ background: "var(--bg-1)" }}>
            {status.schedule.map((s) => {
              const days = editDays[s.user_id] ?? s.days_of_week;
              const changed = daysChanged(s.user_id);
              return (
                <div key={s.user_id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="t-small font-mono mb-2" style={{ color: "var(--fg-0)" }}>{s.email}</p>
                      <div className="flex gap-1 flex-wrap">
                        {DAY_NAMES.map((name, d) => {
                          const active = days.includes(d);
                          return (
                            <button
                              key={d}
                              onClick={() => toggleDay(s.user_id, d)}
                              className="px-2 py-0.5 t-micro border transition-colors"
                              style={{
                                background: active ? "var(--accent)" : "transparent",
                                color: active ? "#fff" : "var(--fg-3)",
                                borderColor: active ? "var(--accent)" : "var(--line)",
                              }}
                            >
                              {name.slice(0, 3)}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    {changed && (
                      <button
                        onClick={() => saveShift(s.user_id)}
                        disabled={saving === s.user_id}
                        className="px-3 py-1.5 t-micro border transition-colors hover:opacity-80 disabled:opacity-40 flex-shrink-0"
                        style={{ color: "var(--accent)", borderColor: "var(--accent)" }}
                      >
                        {saving === s.user_id ? "Saving..." : "Save"}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

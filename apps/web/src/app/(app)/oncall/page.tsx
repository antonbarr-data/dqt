"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Phone, RefreshCw } from "lucide-react";
import { authHeaders } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface ShiftEntry {
  user_id: string;
  email: string;
  name: string | null;
  days_of_week: number[];
}

interface OncallStatus {
  current_oncall: (ShiftEntry & { today: string }) | null;
  upcoming_oncall: (ShiftEntry & { next_day: string; days_until: number }) | null;
  schedule: ShiftEntry[];
  today_name: string;
}

function displayName(s: ShiftEntry): string {
  return s.name ?? s.email;
}

function displayShort(s: ShiftEntry): string {
  if (s.name) return s.name.split(" ")[0];
  return s.email.split("@")[0];
}

function getWeekStart(offset: number): Date {
  const now = new Date();
  const day = now.getDay(); // 0=Sun..6=Sat
  const mondayOffset = (day === 0 ? -6 : 1 - day) + offset * 7;
  const monday = new Date(now);
  monday.setDate(now.getDate() + mondayOffset);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

function formatWeekRange(weekStart: Date): string {
  const end = new Date(weekStart);
  end.setDate(weekStart.getDate() + 6);
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  const startStr = weekStart.toLocaleDateString(undefined, opts);
  const endStr = end.toLocaleDateString(undefined, { ...opts, year: "numeric" });
  return `${startStr} – ${endStr}`;
}

function dayDate(weekStart: Date, dayIndex: number): string {
  const d = new Date(weekStart);
  d.setDate(weekStart.getDate() + dayIndex);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function OncallPage() {
  const [status, setStatus] = useState<OncallStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [redistributing, setRedistributing] = useState(false);
  const [editDays, setEditDays] = useState<Record<string, number[]>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [weekOffset, setWeekOffset] = useState(0);

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
    return <div className="p-6"><p className="t-small" style={{ color: "var(--fg-2)" }}>Loading...</p></div>;
  }

  if (!status) return null;

  const coverage: Record<number, ShiftEntry> = {};
  for (const s of status.schedule) {
    for (const d of s.days_of_week) coverage[d] = s;
  }

  const weekStart = getWeekStart(weekOffset);
  const todayDayIndex = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1; // Mon=0

  // Is today in the displayed week?
  const todayInView = weekOffset === 0;

  return (
    <div className="p-6 space-y-5 fade-in">
      {/* Header */}
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

      <div className="grid grid-cols-[1fr_320px] gap-5 items-start">
        {/* Left: banner + weekly grid */}
        <div className="space-y-4">
          {/* Current on-call banner */}
          {weekOffset === 0 && (
            status.current_oncall ? (
              <div
                className="border p-4 flex items-start gap-3"
                style={{ borderColor: "var(--accent)", background: "rgba(99,102,241,0.06)" }}
              >
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--pass)", marginTop: 5, flexShrink: 0, display: "inline-block" }} />
                <div>
                  <p className="t-micro mb-0.5" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                    On-call now — {status.today_name}
                  </p>
                  <p className="t-small" style={{ color: "var(--fg-0)" }}>
                    {displayName(status.current_oncall)}
                    {status.current_oncall.name && (
                      <span className="font-mono ml-2" style={{ color: "var(--fg-3)" }}>{status.current_oncall.email}</span>
                    )}
                  </p>
                </div>
              </div>
            ) : (
              <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
                <p className="t-micro mb-1" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  No one on call today ({status.today_name})
                </p>
                {status.upcoming_oncall && (
                  <p className="t-small" style={{ color: "var(--fg-2)" }}>
                    Next:{" "}
                    <span style={{ color: "var(--fg-0)" }}>{displayName(status.upcoming_oncall)}</span>
                    <span style={{ color: "var(--fg-3)" }}> on {status.upcoming_oncall.next_day} ({status.upcoming_oncall.days_until}d)</span>
                  </p>
                )}
              </div>
            )
          )}

          {/* Week navigation + grid */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setWeekOffset((w) => w - 1)}
                  className="p-1 border border-line transition-colors hover:opacity-80"
                  style={{ color: "var(--fg-2)" }}
                  title="Previous week"
                >
                  <ChevronLeft size={13} strokeWidth={2} />
                </button>
                <span className="t-small font-mono" style={{ color: weekOffset === 0 ? "var(--accent)" : "var(--fg-1)" }}>
                  {weekOffset === 0 ? "This week" : weekOffset === 1 ? "Next week" : weekOffset === -1 ? "Last week" : formatWeekRange(weekStart)}
                  {" "}
                  <span style={{ color: "var(--fg-3)" }}>({formatWeekRange(weekStart)})</span>
                </span>
                <button
                  onClick={() => setWeekOffset((w) => w + 1)}
                  className="p-1 border border-line transition-colors hover:opacity-80"
                  style={{ color: "var(--fg-2)" }}
                  title="Next week"
                >
                  <ChevronRight size={13} strokeWidth={2} />
                </button>
                {weekOffset !== 0 && (
                  <button
                    onClick={() => setWeekOffset(0)}
                    className="t-micro px-2 py-0.5 border border-line hover:opacity-80"
                    style={{ color: "var(--fg-3)" }}
                  >
                    Today
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-7 gap-px" style={{ background: "var(--line)" }}>
              {DAY_NAMES.map((name, d) => {
                const entry = coverage[d];
                const isToday = todayInView && d === todayDayIndex;
                return (
                  <div
                    key={d}
                    className="px-2 py-3"
                    style={{
                      background: isToday ? "rgba(99,102,241,0.08)" : "var(--bg-1)",
                      borderBottom: isToday ? "2px solid var(--accent)" : undefined,
                    }}
                  >
                    <p className="t-micro mb-0.5" style={{ color: isToday ? "var(--accent)" : "var(--fg-3)", letterSpacing: "0.06em" }}>
                      {DAY_SHORT[d]}
                    </p>
                    <p className="t-micro font-mono mb-1.5" style={{ color: "var(--fg-3)" }}>
                      {dayDate(weekStart, d)}
                    </p>
                    {entry ? (
                      <p className="t-micro" style={{ color: "var(--fg-0)", wordBreak: "break-word" }} title={entry.email}>
                        {displayShort(entry)}
                      </p>
                    ) : (
                      <p className="t-micro" style={{ color: "var(--fail)" }}>--</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: rotation members */}
        <div>
          <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Rotation members</p>
          {status.schedule.length === 0 ? (
            <div className="border border-line p-4 text-center" style={{ background: "var(--bg-1)" }}>
              <p className="t-small" style={{ color: "var(--fg-3)" }}>
                No eligible users yet.{" "}
                <a href="/settings/users" style={{ color: "var(--accent)" }}>Manage users</a>
              </p>
            </div>
          ) : (
            <div className="border border-line divide-y divide-line" style={{ background: "var(--bg-1)" }}>
              {status.schedule.map((s) => {
                const days = editDays[s.user_id] ?? s.days_of_week;
                const changed = daysChanged(s.user_id);
                return (
                  <div key={s.user_id} className="px-3 py-3">
                    <div className="mb-2">
                      <p className="t-small" style={{ color: "var(--fg-0)" }}>{displayName(s)}</p>
                      {s.name && <p className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{s.email}</p>}
                    </div>
                    <div className="flex gap-1 flex-wrap mb-2">
                      {DAY_NAMES.map((name, d) => {
                        const active = days.includes(d);
                        return (
                          <button
                            key={d}
                            onClick={() => toggleDay(s.user_id, d)}
                            className="px-1.5 py-0.5 t-micro border transition-colors"
                            style={{
                              background: active ? "var(--accent)" : "transparent",
                              color: active ? "#fff" : "var(--fg-3)",
                              borderColor: active ? "var(--accent)" : "var(--line)",
                            }}
                          >
                            {DAY_SHORT[d]}
                          </button>
                        );
                      })}
                    </div>
                    {changed && (
                      <button
                        onClick={() => saveShift(s.user_id)}
                        disabled={saving === s.user_id}
                        className="px-2 py-1 t-micro border transition-colors hover:opacity-80 disabled:opacity-40"
                        style={{ color: "var(--accent)", borderColor: "var(--accent)" }}
                      >
                        {saving === s.user_id ? "Saving..." : "Save"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

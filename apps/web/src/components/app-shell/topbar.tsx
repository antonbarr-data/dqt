"use client";

import { useState, useEffect } from "react";
import { Search, RefreshCw, Bell } from "lucide-react";
import { getToken, decodeToken } from "@/lib/auth";

export function Topbar() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [statusText] = useState("9.4k tests/min · all engines healthy");

  useEffect(() => {
    const stored = localStorage.getItem("dqt-theme") as "dark" | "light" | null;
    if (stored) {
      setTheme(stored);
      document.documentElement.setAttribute("data-theme", stored);
    }
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("dqt-theme", next);
    document.documentElement.setAttribute("data-theme", next);
  }

  return (
    <header
      className="flex items-center gap-3 px-4 border-b border-line"
      style={{ height: 44, background: "var(--bg-1)", flexShrink: 0 }}
    >
      {/* search */}
      <div
        className="flex items-center gap-2 border border-line px-2.5 py-1"
        style={{ background: "var(--bg-2)", width: 320 }}
      >
        <Search size={11} strokeWidth={1.6} style={{ color: "var(--fg-3)", flexShrink: 0 }} />
        <input
          type="text"
          placeholder="Search datasets, incidents, tests…"
          className="flex-1 bg-transparent t-small outline-none"
          style={{ color: "var(--fg-1)" }}
        />
        <kbd
          className="t-micro px-1 border border-line"
          style={{ color: "var(--fg-3)", background: "var(--bg-3)", lineHeight: "18px" }}
        >
          ⌘K
        </kbd>
      </div>

      <div className="flex-1" />

      {/* status pill */}
      <div className="flex items-center gap-2">
        <span
          className="t-micro"
          style={{ color: "var(--pass)" }}
        >
          ●
        </span>
        <span className="t-small" style={{ color: "var(--fg-1)" }}>
          {statusText}
        </span>
      </div>

      <div className="w-px self-stretch" style={{ background: "var(--line)", margin: "10px 0" }} />

      {/* icon actions */}
      <button
        onClick={toggleTheme}
        className="w-7 h-7 flex items-center justify-center border border-line t-small transition-colors hover:bg-bg-2"
        style={{ color: "var(--fg-2)" }}
        aria-label="Toggle theme"
        title="Toggle theme"
      >
        ◐
      </button>

      <button
        className="w-7 h-7 flex items-center justify-center border border-line transition-colors hover:bg-bg-2"
        style={{ color: "var(--fg-2)" }}
        title="Refresh"
      >
        <RefreshCw size={12} strokeWidth={1.6} />
      </button>

      <button
        className="w-7 h-7 flex items-center justify-center border border-line transition-colors hover:bg-bg-2"
        style={{ color: "var(--fg-2)" }}
        title="Notifications"
      >
        <Bell size={12} strokeWidth={1.6} />
      </button>
    </header>
  );
}

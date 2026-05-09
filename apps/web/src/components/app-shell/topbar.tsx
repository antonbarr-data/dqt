"use client";

import { useState, useEffect } from "react";
import { Search } from "lucide-react";

export function Topbar() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

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
      className="flex items-center gap-4 px-4 border-b border-line"
      style={{ height: 44, background: "var(--bg-1)", flexShrink: 0 }}
    >
      {/* logo */}
      <span
        className="font-mono font-light select-none"
        style={{
          color: "var(--accent)",
          fontSize: 15,
          letterSpacing: "-0.05em",
          fontWeight: 300,
          whiteSpace: "nowrap",
        }}
      >
        dqt
      </span>

      {/* search */}
      <div className="flex-1 flex items-center gap-2 border border-line px-2.5 py-1" style={{ background: "var(--bg-2)", maxWidth: 440 }}>
        <Search size={12} strokeWidth={1.6} style={{ color: "var(--fg-2)", flexShrink: 0 }} />
        <input
          type="text"
          placeholder="Search datasets, checks, metrics..."
          className="flex-1 bg-transparent t-small outline-none"
          style={{ color: "var(--fg-0)" }}
        />
        <kbd className="t-micro px-1 border border-line" style={{ color: "var(--fg-3)", background: "var(--bg-3)" }}>
          ⌘K
        </kbd>
      </div>

      <div className="flex-1" />

      {/* theme toggle */}
      <button
        onClick={toggleTheme}
        className="w-7 h-7 flex items-center justify-center border border-line t-small transition-colors hover:bg-bg-2"
        style={{ color: "var(--fg-1)" }}
        aria-label="Toggle theme"
        title="Toggle dark/light"
      >
        ◐
      </button>

      {/* user avatar */}
      <div
        className="w-7 h-7 flex items-center justify-center t-micro font-medium border border-line"
        style={{
          background: "var(--accent-bg)",
          color: "var(--accent)",
          fontFamily: "var(--font-jetbrains-mono)",
          letterSpacing: 0,
        }}
        title="Jamie Lin"
      >
        JL
      </div>
    </header>
  );
}

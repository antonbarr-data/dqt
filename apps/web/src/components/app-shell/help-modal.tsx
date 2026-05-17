"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

interface HelpModalProps { open: boolean; onClose: () => void }

const SHORTCUTS = [
  { keys: ["/"], label: "Open search / command palette" },
  { keys: ["Ctrl", "K"], label: "Open Ask (AI question)" },
  { keys: ["Ctrl", "/"], label: "Open this help panel" },
  { keys: ["Esc"], label: "Close any open panel" },
];

const NAV = [
  { key: "Overview", href: "/overview" },
  { key: "Ask", href: "/ask" },
  { key: "Subscriptions", href: "/subscriptions" },
  { key: "Datasets", href: "/datasets" },
  { key: "Lineage", href: "/lineage" },
  { key: "Metrics", href: "/metrics" },
  { key: "Causality", href: "/causality" },
  { key: "Incidents", href: "/incidents" },
  { key: "Checks", href: "/checks" },
];

export function HelpModal({ open, onClose }: HelpModalProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-40" style={{ background: "rgba(0,0,0,0.45)" }} onClick={onClose} />
      <div
        className="fixed top-1/2 left-1/2 z-50"
        style={{ width: 480, transform: "translate(-50%, -50%)", background: "var(--bg-1)", border: "1px solid var(--line)" }}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-line">
          <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Keyboard shortcuts</span>
          <button onClick={onClose} className="hover:opacity-70">
            <X size={14} strokeWidth={1.6} style={{ color: "var(--fg-2)" }} />
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.10em", textTransform: "uppercase" }}>Shortcuts</p>
            <div className="space-y-1.5">
              {SHORTCUTS.map(s => (
                <div key={s.label} className="flex items-center justify-between">
                  <span className="t-small" style={{ color: "var(--fg-1)" }}>{s.label}</span>
                  <div className="flex gap-1">
                    {s.keys.map(k => (
                      <kbd key={k} className="t-micro px-1.5 py-0.5 border border-line" style={{ color: "var(--fg-2)", background: "var(--bg-2)" }}>{k}</kbd>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.10em", textTransform: "uppercase" }}>Navigation</p>
            <div className="flex flex-wrap gap-2">
              {NAV.map(n => (
                <a key={n.key} href={n.href} onClick={onClose} className="t-micro px-2 py-1 border border-line hover:border-accent transition-colors" style={{ color: "var(--fg-1)", background: "var(--bg-2)" }}>
                  {n.key}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

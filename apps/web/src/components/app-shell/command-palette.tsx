"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, LayoutDashboard, Database, Table2, GitBranch, BarChart2, Network, AlertTriangle, CheckSquare, BookOpen, Shield, ScrollText, Phone, ClipboardList } from "lucide-react";

interface Item {
  id: string;
  group: string;
  label: string;
  sub?: string;
  href: string;
  icon?: React.ReactNode;
}

const NAV_ITEMS: Item[] = [
  { id: "nav-overview",   group: "Navigation", label: "Overview",             href: "/overview",   icon: <LayoutDashboard size={13} strokeWidth={1.6} /> },
  { id: "nav-sources",    group: "Navigation", label: "Sources",              href: "/sources",    icon: <Database size={13} strokeWidth={1.6} /> },
  { id: "nav-datasets",   group: "Navigation", label: "Datasets",             href: "/datasets",   icon: <Table2 size={13} strokeWidth={1.6} /> },
  { id: "nav-lineage",    group: "Navigation", label: "Lineage",              href: "/lineage",    icon: <GitBranch size={13} strokeWidth={1.6} /> },
  { id: "nav-metrics",    group: "Navigation", label: "Metrics",              href: "/metrics",    icon: <BarChart2 size={13} strokeWidth={1.6} /> },
  { id: "nav-causality",  group: "Navigation", label: "Causality",            href: "/causality",  icon: <Network size={13} strokeWidth={1.6} /> },
  { id: "nav-incidents",  group: "Navigation", label: "Incidents",            href: "/incidents",  icon: <AlertTriangle size={13} strokeWidth={1.6} /> },
  { id: "nav-checks",     group: "Navigation", label: "Checks",               href: "/checks",     icon: <CheckSquare size={13} strokeWidth={1.6} /> },
  { id: "nav-catalog",    group: "Navigation", label: "Catalog",              href: "/catalog",    icon: <BookOpen size={13} strokeWidth={1.6} /> },
  { id: "nav-policies",   group: "Navigation", label: "Policies",             href: "/policies",   icon: <Shield size={13} strokeWidth={1.6} /> },
  { id: "nav-audit",      group: "Navigation", label: "Audit",                href: "/audit",      icon: <ScrollText size={13} strokeWidth={1.6} /> },
  { id: "nav-oncall",     group: "Navigation", label: "On-call",              href: "/oncall",     icon: <Phone size={13} strokeWidth={1.6} /> },
  { id: "nav-tasks",      group: "Navigation", label: "Tasks",                href: "/tasks",      icon: <ClipboardList size={13} strokeWidth={1.6} /> },
];

const DATASET_ITEMS: Item[] = [
  { id: "ds-1", group: "Datasets", label: "gigler_transactions",   sub: "gigler · 1.2M rows",   href: "/datasets/gigler_transactions" },
  { id: "ds-2", group: "Datasets", label: "gig_vendor_stats",      sub: "gigler · 84K rows",    href: "/datasets/gig_vendor_stats" },
  { id: "ds-3", group: "Datasets", label: "gig_prices",            sub: "gigler · 320K rows",   href: "/datasets/gig_prices" },
  { id: "ds-4", group: "Datasets", label: "marketing_campaigns",   sub: "marketing · 18K rows", href: "/datasets/marketing_campaigns" },
];

const INCIDENT_ITEMS: Item[] = [
  { id: "inc-1", group: "Incidents", label: "#1 null_fraction — platform_fee_usd",   sub: "fail · open",   href: "/incidents/1" },
  { id: "inc-2", group: "Incidents", label: "#2 value_in_range — amount_usd",        sub: "warn · open",   href: "/incidents/2" },
  { id: "inc-3", group: "Incidents", label: "#3 stl_residual_zscore — daily_active", sub: "fail · open",   href: "/incidents/3" },
];

const ALL_ITEMS = [...NAV_ITEMS, ...DATASET_ITEMS, ...INCIDENT_ITEMS];

function grouped(items: Item[]): [string, Item[]][] {
  const map = new Map<string, Item[]>();
  for (const item of items) {
    if (!map.has(item.group)) map.set(item.group, []);
    map.get(item.group)!.push(item);
  }
  return Array.from(map.entries());
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = query.trim()
    ? ALL_ITEMS.filter((i) =>
        i.label.toLowerCase().includes(query.toLowerCase()) ||
        (i.sub ?? "").toLowerCase().includes(query.toLowerCase())
      )
    : ALL_ITEMS;

  const flatItems = grouped(filtered).flatMap(([, items]) => items);

  useEffect(() => {
    setCursor(0);
  }, [query]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setCursor(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  const navigate = useCallback((href: string) => {
    onClose();
    router.push(href as never);
  }, [onClose, router]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!open) return;
      if (e.key === "Escape") { onClose(); return; }
      if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, flatItems.length - 1)); }
      if (e.key === "ArrowUp")   { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
      if (e.key === "Enter" && flatItems[cursor]) { navigate(flatItems[cursor].href); }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, cursor, flatItems, navigate, onClose]);

  // scroll active item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${cursor}"]`) as HTMLElement | null;
    el?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (!open) return null;

  const groups = grouped(filtered);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center"
      style={{ background: "rgba(0,0,0,0.6)", paddingTop: 80 }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="border border-line"
        style={{ background: "var(--bg-1)", width: 560, maxHeight: 440, display: "flex", flexDirection: "column", boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}
      >
        {/* search input */}
        <div className="flex items-center gap-2.5 px-3 py-2.5 border-b border-line" style={{ flexShrink: 0 }}>
          <Search size={13} strokeWidth={1.6} style={{ color: "var(--fg-3)", flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search datasets, incidents, pages…"
            className="flex-1 bg-transparent t-small outline-none"
            style={{ color: "var(--fg-0)" }}
          />
          <kbd className="t-micro px-1.5 border border-line" style={{ color: "var(--fg-3)", background: "var(--bg-2)", lineHeight: "18px" }}>esc</kbd>
        </div>

        {/* results */}
        <div ref={listRef} className="overflow-y-auto flex-1">
          {filtered.length === 0 ? (
            <div className="px-4 py-6 text-center t-small" style={{ color: "var(--fg-3)" }}>No results</div>
          ) : (
            groups.map(([group, items]) => {
              return (
                <div key={group}>
                  <div
                    className="px-3 py-1 t-micro"
                    style={{ color: "var(--fg-3)", letterSpacing: "0.10em", textTransform: "uppercase", background: "var(--bg-0)" }}
                  >
                    {group}
                  </div>
                  {items.map((item) => {
                    const idx = flatItems.indexOf(item);
                    const active = idx === cursor;
                    return (
                      <button
                        key={item.id}
                        data-idx={idx}
                        onClick={() => navigate(item.href)}
                        onMouseEnter={() => setCursor(idx)}
                        className="w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors"
                        style={{ background: active ? "var(--bg-2)" : "transparent" }}
                      >
                        {item.icon && (
                          <span style={{ color: active ? "var(--accent)" : "var(--fg-2)", flexShrink: 0 }}>
                            {item.icon}
                          </span>
                        )}
                        {!item.icon && (
                          <span
                            style={{ display: "inline-block", width: 5, height: 5, background: active ? "var(--accent)" : "var(--fg-3)", flexShrink: 0, marginLeft: 4 }}
                          />
                        )}
                        <span className="t-small flex-1" style={{ color: active ? "var(--fg-0)" : "var(--fg-1)" }}>{item.label}</span>
                        {item.sub && (
                          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{item.sub}</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>

        {/* footer hint */}
        <div
          className="flex items-center gap-3 px-3 py-1.5 border-t border-line t-micro"
          style={{ color: "var(--fg-3)", flexShrink: 0 }}
        >
          <span><kbd className="px-1 border border-line" style={{ background: "var(--bg-2)" }}>↑↓</kbd> navigate</span>
          <span><kbd className="px-1 border border-line" style={{ background: "var(--bg-2)" }}>↵</kbd> open</span>
          <span><kbd className="px-1 border border-line" style={{ background: "var(--bg-2)" }}>esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}

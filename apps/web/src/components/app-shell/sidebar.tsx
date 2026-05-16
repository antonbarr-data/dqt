"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Database,
  Table2,
  GitBranch,
  BarChart2,
  Network,
  AlertTriangle,
  CheckSquare,
  Users,
  BookOpen,
  Shield,
  ScrollText,
  Phone,
  ClipboardList,
} from "lucide-react";
import { clsx } from "clsx";
import { isSysAdmin } from "@/lib/auth";

const NAV_GROUPS = [
  {
    label: "Analytics Warehouse",
    items: [
      { label: "Overview", href: "/overview", icon: LayoutDashboard, count: null },
    ],
  },
  {
    label: "Warehouse",
    items: [
      { label: "Sources", href: "/sources", icon: Database, count: null },
      { label: "Datasets", href: "/datasets", icon: Table2, count: null },
      { label: "Lineage", href: "/lineage", icon: GitBranch, count: null },
    ],
  },
  {
    label: "Semantic Layer",
    items: [
      { label: "Metrics", href: "/metrics", icon: BarChart2, count: null },
      { label: "Causality", href: "/causality", icon: Network, count: null },
    ],
  },
  {
    label: "Watch",
    items: [
      { label: "Incidents", href: "/incidents", icon: AlertTriangle, count: null, countFail: true },
      { label: "Tests", href: "/tests", icon: CheckSquare, count: null },
    ],
  },
  {
    label: "Govern",
    items: [
      { label: "Catalog", href: "/catalog", icon: BookOpen, count: null },
      { label: "Policies", href: "/policies", icon: Shield, count: null },
      { label: "Audit", href: "/audit", icon: ScrollText, count: null },
    ],
  },
  {
    label: "Team",
    items: [
      { label: "On-call", href: "/oncall", icon: Phone, count: null },
      { label: "Tasks", href: "/tasks", icon: ClipboardList, count: null },
    ],
  },
];

const SYSADMIN_NAV = [
  { label: "Users", href: "/settings/users", icon: Users, count: null },
];

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [sysAdmin, setSysAdmin] = useState(false);

  useEffect(() => {
    setSysAdmin(isSysAdmin());
  }, []);

  return (
    <aside
      style={{ width: 52, flexShrink: 0, position: "relative", zIndex: 40 }}
    >
      {/* overlay panel — always absolute, width animates */}
      <div
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: open ? 224 : 52,
          height: "100%",
          background: "var(--bg-1)",
          borderRight: "1px solid var(--line)",
          transition: "width 0.18s ease",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          boxShadow: open ? "2px 0 12px rgba(0,0,0,0.2)" : "none",
        }}
      >
      <nav className="flex-1 overflow-y-auto py-3 no-scrollbar">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-1">
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href as never}
                  className={clsx(
                    "flex items-center gap-3 t-body transition-colors",
                    open ? "px-4 py-2" : "justify-center py-2",
                    active ? "border-l-2 border-accent" : "border-l-2 border-transparent hover:bg-bg-2"
                  )}
                  style={{ color: "var(--fg-0)", background: active ? "var(--bg-2)" : undefined }}
                  title={!open ? item.label : undefined}
                >
                  <Icon
                    size={16}
                    strokeWidth={1.6}
                    style={{ flexShrink: 0, color: active ? "var(--accent)" : "var(--fg-1)" }}
                  />
                  {open && (
                    <>
                      <span className="flex-1 whitespace-nowrap">{item.label}</span>
                      {item.count !== null && (
                        <span
                          className="t-small tabular-nums"
                          style={{
                            color: "countFail" in item && item.countFail ? "var(--fail)" : "var(--fg-2)",
                            fontFamily: "var(--font-jetbrains-mono)",
                          }}
                        >
                          {item.count}
                        </span>
                      )}
                    </>
                  )}
                </Link>
              );
            })}
          </div>
        ))}

        {sysAdmin && (
          <div className="mb-1">
            {SYSADMIN_NAV.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href as never}
                  className={clsx(
                    "flex items-center gap-3 t-body transition-colors",
                    open ? "px-4 py-2" : "justify-center py-2",
                    active ? "border-l-2 border-accent" : "border-l-2 border-transparent hover:bg-bg-2"
                  )}
                  style={{ color: "var(--fg-0)", background: active ? "var(--bg-2)" : undefined }}
                  title={!open ? item.label : undefined}
                >
                  <Icon size={16} strokeWidth={1.6} style={{ flexShrink: 0, color: active ? "var(--accent)" : "var(--fg-1)" }} />
                  {open && <span className="flex-1 whitespace-nowrap">{item.label}</span>}
                </Link>
              );
            })}
          </div>
        )}
      </nav>
      </div>
    </aside>
  );
}

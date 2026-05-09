"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Database,
  Table2,
  GitBranch,
  BarChart2,
  Network,
  AlertTriangle,
  CheckSquare,
  BookOpen,
  Shield,
  FileText,
  Phone,
  ClipboardList,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { clsx } from "clsx";

const NAV_GROUPS = [
  {
    label: "Warehouse",
    items: [
      { label: "Sources", href: "/sources", icon: Database },
      { label: "Datasets", href: "/datasets", icon: Table2 },
      { label: "Lineage", href: "/lineage", icon: GitBranch },
    ],
  },
  {
    label: "Semantic Layer",
    items: [
      { label: "Metrics", href: "/metrics", icon: BarChart2 },
      { label: "Causality", href: "/causality", icon: Network },
    ],
  },
  {
    label: "Watch",
    items: [
      { label: "Incidents", href: "/incidents", icon: AlertTriangle },
      { label: "Tests", href: "/tests", icon: CheckSquare },
    ],
  },
  {
    label: "Govern",
    items: [
      { label: "Catalog", href: "/catalog", icon: BookOpen },
      { label: "Policies", href: "/policies", icon: Shield },
      { label: "Audit", href: "/audit", icon: FileText },
    ],
  },
  {
    label: "Team",
    items: [
      { label: "On-call", href: "/oncall", icon: Phone },
      { label: "Tasks", href: "/tasks", icon: ClipboardList },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className="flex flex-col border-r border-line transition-all duration-200"
      style={{
        width: collapsed ? 48 : 212,
        background: "var(--bg-1)",
        flexShrink: 0,
      }}
    >
      {/* collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-end px-3 py-2 border-b border-line"
        style={{ color: "var(--fg-2)", minHeight: 44 }}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? (
          <ChevronRight size={14} strokeWidth={1.6} />
        ) : (
          <ChevronLeft size={14} strokeWidth={1.6} />
        )}
      </button>

      {/* nav groups */}
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-4">
            {!collapsed && (
              <div
                className="px-3 py-1 t-micro"
                style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}
              >
                {group.label}
              </div>
            )}
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href as never}
                  className={clsx(
                    "flex items-center gap-2.5 px-3 py-1.5 t-small transition-colors",
                    active
                      ? "border-l-2 border-accent text-fg-0"
                      : "border-l-2 border-transparent hover:bg-bg-2"
                  )}
                  style={{
                    color: active ? "var(--fg-0)" : "var(--fg-1)",
                    background: active ? "var(--bg-2)" : undefined,
                  }}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon
                    size={14}
                    strokeWidth={1.6}
                    style={{ flexShrink: 0, color: active ? "var(--accent)" : "var(--fg-2)" }}
                  />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* footer */}
      <div
        className="border-t border-line px-3 py-2.5 t-micro"
        style={{ color: "var(--fg-2)" }}
      >
        {collapsed ? (
          <Phone size={12} strokeWidth={1.6} style={{ color: "var(--pass)" }} />
        ) : (
          <span>
            <span style={{ color: "var(--pass)" }}>●</span>{" "}
            <span>Jamie Lin · on-call</span>
          </span>
        )}
      </div>
    </aside>
  );
}

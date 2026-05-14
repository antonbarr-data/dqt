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
  Bookmark,
  Users,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Shield,
  ScrollText,
  Phone,
  ClipboardList,
} from "lucide-react";
import { clsx } from "clsx";
import { isSysAdmin, decodeToken, getToken } from "@/lib/auth";
import { DQT_VERSION } from "@/lib/version";

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

const SAVED_VIEWS = [
  { label: "My on-call queue", count: 3 },
  { label: "Critical fct.* tables", count: 2 },
  { label: "New tests — last 7d", count: 18 },
];

const SYSADMIN_NAV = [
  { label: "Users", href: "/settings/users", icon: Users, count: null },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [sysAdmin, setSysAdmin] = useState(false);
  const [userInitials, setUserInitials] = useState("?");
  const [userName, setUserName] = useState("User");

  useEffect(() => {
    setSysAdmin(isSysAdmin());
    const token = getToken();
    if (token) {
      const payload = decodeToken(token);
      if (payload) {
        const email = payload.email ?? "";
        setUserInitials(email.slice(0, 2).toUpperCase());
        setUserName(email.split("@")[0]);
      }
    }
  }, []);

  return (
    <aside
      className="flex flex-col border-r border-line transition-all duration-200"
      style={{
        width: collapsed ? 56 : 224,
        background: "var(--bg-1)",
        flexShrink: 0,
      }}
    >
      {/* logo + version */}
      <div
        className="flex items-center justify-between border-b border-line"
        style={{ minHeight: 48, padding: collapsed ? "0 14px" : "0 16px" }}
      >
        {collapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            style={{ color: "var(--accent)", fontSize: 13, fontFamily: "var(--font-jetbrains-mono)", fontWeight: 300, letterSpacing: "-0.05em" }}
            title="Expand sidebar"
          >
            dqt
          </button>
        ) : (
          <>
            <span style={{ color: "var(--accent)", fontSize: 17, fontFamily: "var(--font-jetbrains-mono)", fontWeight: 300, letterSpacing: "-0.05em" }}>
              dqt
            </span>
            <div className="flex items-center gap-2">
              <span className="t-small" style={{ color: "var(--fg-2)" }}>v{DQT_VERSION}</span>
              <button
                onClick={() => setCollapsed(true)}
                className="flex items-center justify-center"
                style={{ color: "var(--fg-2)", width: 18, height: 18 }}
                aria-label="Collapse sidebar"
              >
                <ChevronLeft size={14} strokeWidth={1.6} />
              </button>
            </div>
          </>
        )}
      </div>

      {/* nav groups */}
      <nav className="flex-1 overflow-y-auto py-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-4">
            {!collapsed && (
              <div
                className="px-4 py-1 t-small"
                style={{ color: "var(--fg-1)", letterSpacing: "0.10em", textTransform: "uppercase", fontWeight: 500 }}
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
                    "flex items-center gap-3 t-body transition-colors",
                    collapsed ? "justify-center py-3" : "px-4 py-2",
                    active
                      ? "border-l-2 border-accent"
                      : "border-l-2 border-transparent hover:bg-bg-2"
                  )}
                  style={{
                    color: active ? "var(--fg-0)" : "var(--fg-0)",
                    background: active ? "var(--bg-2)" : undefined,
                  }}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon
                    size={16}
                    strokeWidth={1.6}
                    style={{ flexShrink: 0, color: active ? "var(--accent)" : "var(--fg-1)" }}
                  />
                  {!collapsed && (
                    <>
                      <span className="flex-1">{item.label}</span>
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

        {/* saved views */}
        {!collapsed && (
          <div className="mb-4">
            <div className="px-4 py-1 t-small" style={{ color: "var(--fg-1)", letterSpacing: "0.10em", textTransform: "uppercase", fontWeight: 500 }}>
              Saved Views
            </div>
            {SAVED_VIEWS.map((v) => (
              <div
                key={v.label}
                className="flex items-center gap-3 px-4 py-2 border-l-2 border-transparent t-body transition-colors hover:bg-bg-2 cursor-pointer"
                style={{ color: "var(--fg-0)" }}
              >
                <Bookmark size={14} strokeWidth={1.6} style={{ color: "var(--fg-1)", flexShrink: 0 }} />
                <span className="flex-1 truncate">{v.label}</span>
                <span className="t-small tabular-nums" style={{ color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)" }}>{v.count}</span>
              </div>
            ))}
          </div>
        )}

        {/* sysadmin section */}
        {sysAdmin && (
          <div className="mb-4">
            {!collapsed && (
              <div className="px-4 py-1 t-small" style={{ color: "var(--fg-1)", letterSpacing: "0.10em", textTransform: "uppercase", fontWeight: 500 }}>
                Admin
              </div>
            )}
            {SYSADMIN_NAV.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href as never}
                  className={clsx(
                    "flex items-center gap-3 t-body transition-colors",
                    collapsed ? "justify-center py-3" : "px-4 py-2",
                    active ? "border-l-2 border-accent" : "border-l-2 border-transparent hover:bg-bg-2"
                  )}
                  style={{ color: "var(--fg-0)", background: active ? "var(--bg-2)" : undefined }}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon size={16} strokeWidth={1.6} style={{ flexShrink: 0, color: active ? "var(--accent)" : "var(--fg-1)" }} />
                  {!collapsed && <span className="flex-1">{item.label}</span>}
                </Link>
              );
            })}
          </div>
        )}
      </nav>

      {/* footer — user + on-call */}
      <div className="border-t border-line">
        {collapsed ? (
          <div className="flex flex-col items-center gap-3 py-3">
            <div
              className="w-7 h-7 flex items-center justify-center t-small font-medium"
              style={{ background: "var(--accent-bg)", color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {userInitials}
            </div>
            <button onClick={() => setCollapsed(false)} style={{ color: "var(--fg-1)" }} title="Expand sidebar">
              <ChevronRight size={14} strokeWidth={1.6} />
            </button>
          </div>
        ) : (
          <div className="px-4 py-3 flex items-center gap-3">
            <div
              className="w-7 h-7 flex items-center justify-center t-small font-medium flex-shrink-0"
              style={{ background: "var(--accent-bg)", color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {userInitials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="t-body truncate" style={{ color: "var(--fg-0)" }}>{userName}</p>
              <p className="t-small truncate" style={{ color: "var(--pass)" }}>
                <span style={{ marginRight: 3 }}>●</span>on-call · ends 18:30
              </p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

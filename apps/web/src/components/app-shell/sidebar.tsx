"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
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
  Settings,
  Users,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { clsx } from "clsx";
import { isSysAdmin, decodeToken, getToken, clearToken } from "@/lib/auth";

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
      { label: "Sources", href: "/sources", icon: Database, count: 5 },
      { label: "Datasets", href: "/datasets", icon: Table2, count: 64 },
      { label: "Lineage", href: "/lineage", icon: GitBranch, count: null },
    ],
  },
  {
    label: "Semantic Layer",
    items: [
      { label: "Metrics", href: "/metrics", icon: BarChart2, count: 24 },
      { label: "Causality", href: "/causality", icon: Network, count: null },
    ],
  },
  {
    label: "Watch",
    items: [
      { label: "Incidents", href: "/incidents", icon: AlertTriangle, count: 6 as number | null, countFail: true },
      { label: "Tests", href: "/tests", icon: CheckSquare, count: 734 },
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
  const router = useRouter();
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

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <aside
      className="flex flex-col border-r border-line transition-all duration-200"
      style={{
        width: collapsed ? 48 : 200,
        background: "var(--bg-1)",
        flexShrink: 0,
      }}
    >
      {/* logo + version */}
      <div
        className="flex items-center justify-between border-b border-line"
        style={{ minHeight: 44, padding: collapsed ? "0 12px" : "0 14px" }}
      >
        {collapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            style={{ color: "var(--accent)", fontSize: 14, fontFamily: "var(--font-jetbrains-mono)", fontWeight: 300, letterSpacing: "-0.05em" }}
          >
            d
          </button>
        ) : (
          <>
            <span style={{ color: "var(--accent)", fontSize: 15, fontFamily: "var(--font-jetbrains-mono)", fontWeight: 300, letterSpacing: "-0.05em" }}>
              dqt
            </span>
            <div className="flex items-center gap-2">
              <span className="t-micro" style={{ color: "var(--fg-3)" }}>v0.4.1</span>
              <button
                onClick={() => setCollapsed(true)}
                className="flex items-center justify-center"
                style={{ color: "var(--fg-3)", width: 16, height: 16 }}
                aria-label="Collapse sidebar"
              >
                <ChevronLeft size={12} strokeWidth={1.6} />
              </button>
            </div>
          </>
        )}
      </div>

      {/* nav groups */}
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-3">
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
                    "flex items-center gap-2 px-3 py-1.5 t-small transition-colors",
                    active
                      ? "border-l-2 border-accent"
                      : "border-l-2 border-transparent hover:bg-bg-2"
                  )}
                  style={{
                    color: active ? "var(--fg-0)" : "var(--fg-1)",
                    background: active ? "var(--bg-2)" : undefined,
                  }}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon
                    size={13}
                    strokeWidth={1.6}
                    style={{ flexShrink: 0, color: active ? "var(--accent)" : "var(--fg-2)" }}
                  />
                  {!collapsed && (
                    <>
                      <span className="flex-1">{item.label}</span>
                      {item.count !== null && (
                        <span
                          className="t-micro tabular-nums"
                          style={{
                            color: "countFail" in item && item.countFail ? "var(--fail)" : "var(--fg-3)",
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
          <div className="mb-3">
            <div className="px-3 py-1 t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
              Saved Views
            </div>
            {SAVED_VIEWS.map((v) => (
              <div
                key={v.label}
                className="flex items-center gap-2 px-3 py-1.5 border-l-2 border-transparent t-small transition-colors hover:bg-bg-2 cursor-pointer"
                style={{ color: "var(--fg-1)" }}
              >
                <Bookmark size={11} strokeWidth={1.6} style={{ color: "var(--fg-3)", flexShrink: 0 }} />
                <span className="flex-1 truncate">{v.label}</span>
                <span className="t-micro tabular-nums" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>{v.count}</span>
              </div>
            ))}
          </div>
        )}

        {/* sysadmin section */}
        {sysAdmin && (
          <div className="mb-3">
            {!collapsed && (
              <div className="px-3 py-1 t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
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
                    "flex items-center gap-2 px-3 py-1.5 t-small transition-colors",
                    active ? "border-l-2 border-accent" : "border-l-2 border-transparent hover:bg-bg-2"
                  )}
                  style={{ color: active ? "var(--fg-0)" : "var(--fg-1)", background: active ? "var(--bg-2)" : undefined }}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon size={13} strokeWidth={1.6} style={{ flexShrink: 0, color: active ? "var(--accent)" : "var(--fg-2)" }} />
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
          <div className="flex flex-col items-center gap-2 py-3">
            <div
              className="w-6 h-6 flex items-center justify-center t-micro font-medium"
              style={{ background: "var(--accent-bg)", color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {userInitials}
            </div>
            <button onClick={() => setCollapsed(false)} style={{ color: "var(--fg-3)" }}>
              <ChevronRight size={12} strokeWidth={1.6} />
            </button>
          </div>
        ) : (
          <div className="px-3 py-2.5 flex items-center gap-2">
            <div
              className="w-6 h-6 flex items-center justify-center t-micro font-medium flex-shrink-0"
              style={{ background: "var(--accent-bg)", color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {userInitials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="t-small truncate" style={{ color: "var(--fg-0)" }}>{userName}</p>
              <p className="t-micro truncate" style={{ color: "var(--pass)" }}>
                <span style={{ marginRight: 3 }}>●</span>on-call · ends 18:30
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="flex-shrink-0 p-1 transition-colors hover:opacity-70"
              style={{ color: "var(--fg-3)" }}
              title="Settings / Sign out"
            >
              <Settings size={12} strokeWidth={1.6} />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

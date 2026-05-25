"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import {
  Database,
  Table2,
  BarChart2,
  Network,
  AlertTriangle,
  CheckSquare,
  Users,
  Phone,
  ClipboardList,
  MessageSquare,
  LayoutDashboard,
  Pin,
} from "lucide-react";
import { clsx } from "clsx";
import { isSysAdmin } from "@/lib/auth";

const ALL_NAV_ITEMS = [
  { label: "Overview", href: "/overview", icon: LayoutDashboard },
  { label: "Ask", href: "/ask", icon: MessageSquare },
  { label: "Sources", href: "/sources", icon: Database },
  { label: "Datasets", href: "/datasets", icon: Table2 },
  { label: "Checks", href: "/checks", icon: CheckSquare },
  { label: "Metrics", href: "/metrics", icon: BarChart2 },
  { label: "Causality", href: "/causality", icon: Network },
  { label: "On-call", href: "/oncall", icon: Phone },
  { label: "Tasks", href: "/tasks", icon: ClipboardList },
];

const NAV_GROUPS = [
  {
    label: "Warehouse",
    items: ["Sources", "Datasets"],
  },
  {
    label: "Watch",
    items: ["Overview", "Ask", "Checks"],
  },
  {
    label: "Semantic Layer",
    items: ["Metrics", "Causality"],
  },
  {
    label: "Team",
    items: ["On-call", "Tasks"],
  },
];

const SYSADMIN_NAV = [
  { label: "Users", href: "/settings/users", icon: Users },
];

const PINS_KEY = "dqt-nav-pins";
const LABEL_H = 24;
const ITEM_H = 36;

function loadPins(): string[] {
  try {
    const raw = localStorage.getItem(PINS_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function savePins(pins: string[]) {
  localStorage.setItem(PINS_KEY, JSON.stringify(pins));
}

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [sysAdmin, setSysAdmin] = useState(false);
  const [pins, setPins] = useState<string[]>([]);
  const [hoverPin, setHoverPin] = useState<string | null>(null);

  useEffect(() => {
    setSysAdmin(isSysAdmin());
    setPins(loadPins());
  }, []);

  function togglePin(label: string) {
    setPins((prev) => {
      const next = prev.includes(label)
        ? prev.filter((p) => p !== label)
        : [...prev, label];
      savePins(next);
      return next;
    });
  }

  const itemMap = Object.fromEntries(ALL_NAV_ITEMS.map((i) => [i.label, i]));

  const pinnedItems = pins.map((p) => itemMap[p]).filter(Boolean);

  return (
    <aside style={{ width: 52, flexShrink: 0, position: "relative", zIndex: 40 }}>
      <div
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => { setOpen(false); setHoverPin(null); }}
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

          {/* Pinned section */}
          {pinnedItems.length > 0 && (
            <div className="mb-2">
              {open ? (
                <div
                  className="px-4 t-small whitespace-nowrap overflow-hidden"
                  style={{
                    color: "var(--fg-1)",
                    letterSpacing: "0.10em",
                    textTransform: "uppercase",
                    fontWeight: 500,
                    height: LABEL_H,
                    lineHeight: `${LABEL_H}px`,
                  }}
                >
                  Pinned
                </div>
              ) : (
                <div style={{ height: LABEL_H, display: "flex", alignItems: "center", padding: "0 10px" }}>
                  <div style={{ height: 1, width: "100%", background: "var(--fg-3)" }} />
                </div>
              )}
              {pinnedItems.map((item) => (
                <NavItem
                  key={item.href}
                  item={item}
                  pathname={pathname}
                  open={open}
                  pinned
                  hovered={hoverPin === item.label}
                  onHover={setHoverPin}
                  onPin={togglePin}
                  itemH={ITEM_H}
                />
              ))}
            </div>
          )}

          {/* Regular groups */}
          {NAV_GROUPS.map((group) => {
            const groupItems = group.items
              .map((label) => itemMap[label])
              .filter(Boolean);
            return (
              <div key={group.label} className="mb-2">
                {open ? (
                  <div
                    className="px-4 t-small whitespace-nowrap overflow-hidden"
                    style={{
                      color: "var(--fg-1)",
                      letterSpacing: "0.10em",
                      textTransform: "uppercase",
                      fontWeight: 500,
                      height: LABEL_H,
                      lineHeight: `${LABEL_H}px`,
                    }}
                  >
                    {group.label}
                  </div>
                ) : (
                  <div style={{ height: LABEL_H, display: "flex", alignItems: "center", padding: "0 10px" }}>
                    <div style={{ height: 1, width: "100%", background: "var(--fg-3)" }} />
                  </div>
                )}
                {groupItems.map((item) => (
                  <NavItem
                    key={item.href}
                    item={item}
                    pathname={pathname}
                    open={open}
                    pinned={pins.includes(item.label)}
                    hovered={hoverPin === item.label}
                    onHover={setHoverPin}
                    onPin={togglePin}
                    itemH={ITEM_H}
                  />
                ))}
              </div>
            );
          })}

          {/* Sysadmin */}
          {sysAdmin && (
            <div className="mb-2">
              {open ? (
                <div
                  className="px-4 t-small whitespace-nowrap overflow-hidden"
                  style={{
                    color: "var(--fg-1)",
                    letterSpacing: "0.10em",
                    textTransform: "uppercase",
                    fontWeight: 500,
                    height: LABEL_H,
                    lineHeight: `${LABEL_H}px`,
                  }}
                >
                  Admin
                </div>
              ) : (
                <div style={{ height: LABEL_H, display: "flex", alignItems: "center", padding: "0 10px" }}>
                  <div style={{ height: 1, width: "100%", background: "var(--fg-3)" }} />
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
                      "flex items-center gap-3 px-4 t-small transition-colors",
                      active ? "border-l-2 border-accent" : "border-l-2 border-transparent hover:bg-bg-2"
                    )}
                    style={{ color: active ? "var(--fg-0)" : "var(--fg-1)", background: active ? "var(--bg-2)" : undefined, height: ITEM_H, flexShrink: 0 }}
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

interface NavItemProps {
  item: { label: string; href: string; icon: React.ElementType };
  pathname: string;
  open: boolean;
  pinned: boolean;
  hovered: boolean;
  onHover: (label: string | null) => void;
  onPin: (label: string) => void;
  itemH: number;
}

function NavItem({ item, pathname, open, pinned, hovered, onHover, onPin, itemH }: NavItemProps) {
  const Icon = item.icon;
  const active = pathname === item.href || pathname.startsWith(item.href + "/");

  return (
    <div
      className="relative"
      onMouseEnter={() => onHover(item.label)}
      onMouseLeave={() => onHover(null)}
      style={{ height: itemH }}
    >
      <Link
        href={item.href as never}
        className={clsx(
          "flex items-center gap-3 px-4 t-small transition-colors h-full",
          active ? "border-l-2 border-accent" : "border-l-2 border-transparent hover:bg-bg-2"
        )}
        style={{
          color: active ? "var(--fg-0)" : "var(--fg-1)",
          background: active ? "var(--bg-2)" : undefined,
          flexShrink: 0,
        }}
        title={!open ? item.label : undefined}
      >
        <Icon
          size={16}
          strokeWidth={1.6}
          style={{ flexShrink: 0, color: active ? "var(--accent)" : "var(--fg-1)" }}
        />
        {open && <span className="flex-1 whitespace-nowrap">{item.label}</span>}
      </Link>

      {/* Pin button — always visible when pinned; visible on hover otherwise */}
      {open && (pinned || hovered) && (
        <button
          type="button"
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onPin(item.label); }}
          className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center justify-center"
          style={{
            width: 20,
            height: 20,
            color: pinned ? "var(--accent)" : "var(--fg-1)",
            opacity: 1,
          }}
          title={pinned ? "Unpin" : "Pin to top"}
        >
          <Pin
            size={13}
            strokeWidth={2}
            style={{ transform: pinned ? "rotate(45deg)" : "none", transition: "transform 0.12s" }}
          />
        </button>
      )}
    </div>
  );
}

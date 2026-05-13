"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Bell } from "lucide-react";
import { getToken, decodeToken, clearToken } from "@/lib/auth";
import Image from "next/image";

export function Topbar() {
  const router = useRouter();
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [statusText] = useState("9.4k tests/min · all engines healthy");
  const [accountOpen, setAccountOpen] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [userName, setUserName] = useState("");
  const [userInitials, setUserInitials] = useState("?");
  const [userPicture, setUserPicture] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("dqt-theme") as "dark" | "light" | null;
    if (stored) {
      setTheme(stored);
      document.documentElement.setAttribute("data-theme", stored);
    }
    const token = getToken();
    if (token) {
      const payload = decodeToken(token);
      if (payload) {
        setUserEmail(payload.email ?? "");
        setUserName(payload.email?.split("@")[0] ?? "");
        setUserInitials((payload.email ?? "?").slice(0, 2).toUpperCase());
        setUserPicture(payload.picture ?? null);
      }
    }
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setAccountOpen(false);
      }
    }
    if (accountOpen) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [accountOpen]);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("dqt-theme", next);
    document.documentElement.setAttribute("data-theme", next);
  }

  function handleSignOut() {
    clearToken();
    router.replace("/login");
  }

  return (
    <header
      className="relative flex items-center gap-3 px-4 border-b border-line"
      style={{ height: 44, background: "var(--bg-1)", flexShrink: 0 }}
    >
      {/* centered search */}
      <div
        className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2 border border-line px-2.5 py-1"
        style={{ background: "var(--bg-2)", width: 360 }}
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
        <span className="t-micro" style={{ color: "var(--pass)" }}>●</span>
        <span className="t-small" style={{ color: "var(--fg-1)" }}>{statusText}</span>
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
        title="Notifications"
      >
        <Bell size={12} strokeWidth={1.6} />
      </button>

      <div className="w-px self-stretch" style={{ background: "var(--line)", margin: "10px 0" }} />

      {/* account */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setAccountOpen((v) => !v)}
          className="flex items-center justify-center w-7 h-7 overflow-hidden border border-line transition-colors hover:border-accent"
          style={{ flexShrink: 0 }}
          title={userEmail}
        >
          {userPicture ? (
            <Image
              src={userPicture}
              alt={userName}
              width={28}
              height={28}
              className="w-full h-full object-cover"
              unoptimized
            />
          ) : (
            <span
              className="t-small font-medium"
              style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)", background: "var(--accent-bg)", width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}
            >
              {userInitials}
            </span>
          )}
        </button>

        {accountOpen && (
          <div
            className="absolute right-0 top-full mt-1 border border-line z-50"
            style={{ background: "var(--bg-1)", width: 200, boxShadow: "0 4px 16px rgba(0,0,0,0.3)" }}
          >
            {/* user info header */}
            <div className="px-3 py-2.5 border-b border-line">
              {userPicture && (
                <div className="mb-2">
                  <Image
                    src={userPicture}
                    alt={userName}
                    width={36}
                    height={36}
                    className="object-cover border border-line"
                    unoptimized
                  />
                </div>
              )}
              <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>{userName}</p>
              <p className="t-micro mt-0.5 truncate" style={{ color: "var(--fg-2)" }}>{userEmail}</p>
            </div>

            {/* menu items */}
            <button
              className="w-full text-left px-3 py-2 t-small transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-0)" }}
              onClick={() => { setAccountOpen(false); router.push("/settings" as never); }}
            >
              Account
            </button>
            <button
              className="w-full text-left px-3 py-2 t-small transition-colors hover:bg-bg-2 border-t border-line"
              style={{ color: "var(--fail)" }}
              onClick={handleSignOut}
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

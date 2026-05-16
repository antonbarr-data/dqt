"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Bell } from "lucide-react";
import { getToken, decodeToken, clearToken } from "@/lib/auth";
import Image from "next/image";

interface TestCounts { pass: number; warn: number; fail: number }

function useTestCounts(): TestCounts | null {
  const [counts, setCounts] = useState<TestCounts | null>(null);
  useEffect(() => {
    fetch("/api/v1/checks")
      .then((r) => r.ok ? r.json() : null)
      .then((checks: Array<{ verdict: string }> | null) => {
        if (!checks) return;
        setCounts({
          pass: checks.filter((c) => c.verdict === "pass").length,
          warn: checks.filter((c) => c.verdict === "warn").length,
          fail: checks.filter((c) => c.verdict === "fail").length,
        });
      })
      .catch(() => null);
  }, []);
  return counts;
}

export function Topbar() {
  const router = useRouter();
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [accountOpen, setAccountOpen] = useState(false);
  const testCounts = useTestCounts();
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
      className="flex items-center gap-3 border-b border-line"
      style={{ height: 44, background: "var(--bg-1)", flexShrink: 0, paddingRight: 16 }}
    >
      {/* logo — left-aligned, same width as sidebar */}
      <div
        className="flex items-center gap-2 border-r border-line px-4"
        style={{ width: 224, flexShrink: 0, height: "100%" }}
      >
        <div
          className="flex items-center justify-center"
          style={{ width: 24, height: 24, background: "var(--accent)", flexShrink: 0 }}
        >
          <span style={{ fontSize: 14, fontFamily: "'Hiragino Sans','Yu Gothic','Noto Sans JP',system-ui,sans-serif", fontWeight: 600, color: "#0E0F10", lineHeight: 1 }}>
            質
          </span>
        </div>
        <span style={{ color: "var(--accent)", fontSize: 17, fontFamily: "var(--font-jetbrains-mono)", fontWeight: 300, letterSpacing: "-0.05em" }}>
          dqt
        </span>
      </div>

      {/* centered search */}
      <div className="flex-1 flex justify-center">
      <div
        className="flex items-center gap-2 border border-line px-2.5 py-1"
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
      </div>

      {/* tests status */}
      <div className="flex items-center gap-3">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Tests</span>
        {testCounts ? (
          <>
            <span className="flex items-center gap-1">
              <span style={{ display: "inline-block", width: 6, height: 6, background: "var(--pass)", flexShrink: 0 }} />
              <span className="t-small font-mono" style={{ color: "var(--pass)" }}>{testCounts.pass}</span>
            </span>
            {testCounts.warn > 0 && (
              <span className="flex items-center gap-1">
                <span style={{ display: "inline-block", width: 6, height: 6, background: "var(--warn)", flexShrink: 0 }} />
                <span className="t-small font-mono" style={{ color: "var(--warn)" }}>{testCounts.warn}</span>
              </span>
            )}
            <span className="flex items-center gap-1">
              <span style={{ display: "inline-block", width: 6, height: 6, background: "var(--fail)", flexShrink: 0 }} />
              <span className="t-small font-mono" style={{ color: testCounts.fail > 0 ? "var(--fail)" : "var(--fg-3)" }}>{testCounts.fail}</span>
            </span>
          </>
        ) : (
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>--</span>
        )}
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
            style={{ background: "var(--bg-1)", width: 220, boxShadow: "0 4px 16px rgba(0,0,0,0.25)" }}
          >
            <div className="flex items-center gap-2.5 px-3 py-2.5 border-b border-line">
              <div
                className="flex items-center justify-center flex-shrink-0"
                style={{ width: 28, height: 28, background: "var(--accent-bg)", border: "1px solid var(--line)", overflow: "hidden" }}
              >
                {userPicture ? (
                  <Image src={userPicture} alt={userName} width={28} height={28} className="w-full h-full object-cover" unoptimized />
                ) : (
                  <span className="t-small font-medium" style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
                    {userInitials}
                  </span>
                )}
              </div>
              <div className="min-w-0">
                <p className="t-small truncate" style={{ color: "var(--fg-0)", fontWeight: 500 }}>{userName}</p>
                <p className="t-micro truncate" style={{ color: "var(--fg-3)" }}>{userEmail}</p>
              </div>
            </div>
            <button
              className="w-full text-left px-3 py-2 t-small transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-0)" }}
              onClick={() => { setAccountOpen(false); router.push("/settings" as never); }}
            >
              Account settings
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

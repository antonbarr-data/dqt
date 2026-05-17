"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, decodeToken, clearToken, isSysAdmin } from "@/lib/auth";

export default function SettingsPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [picture, setPicture] = useState<string | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [sysAdmin, setSysAdmin] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("dqt-theme") as "dark" | "light" | null;
    if (stored) setTheme(stored);

    const token = getToken();
    if (token) {
      const payload = decodeToken(token);
      if (payload) {
        setEmail(payload.email ?? "");
        setName(payload.email?.split("@")[0] ?? "");
        setPicture(payload.picture ?? null);
      }
    }
    setSysAdmin(isSysAdmin());
  }, []);

  function applyTheme(t: "dark" | "light") {
    setTheme(t);
    localStorage.setItem("dqt-theme", t);
    document.documentElement.setAttribute("data-theme", t);
  }

  function handleSignOut() {
    clearToken();
    router.replace("/login");
  }

  return (
    <div className="p-6 max-w-2xl space-y-8">
      <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Account settings</h1>

      {/* profile */}
      <section className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div className="px-4 py-3 border-b border-line">
          <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Profile</p>
        </div>
        <div className="px-4 py-4 flex items-center gap-4">
          {picture ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={picture} alt={name} className="w-10 h-10 object-cover border border-line" />
          ) : (
            <div
              className="w-10 h-10 flex items-center justify-center t-small font-medium"
              style={{ background: "var(--accent-bg)", color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {email.slice(0, 2).toUpperCase()}
            </div>
          )}
          <div>
            <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>{name}</p>
            <p className="t-micro mt-0.5" style={{ color: "var(--fg-2)" }}>{email}</p>
          </div>
        </div>
      </section>

      {/* appearance */}
      <section className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div className="px-4 py-3 border-b border-line">
          <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Appearance</p>
        </div>
        <div className="px-4 py-4 flex items-center gap-3">
          {(["dark", "light"] as const).map((t) => (
            <button
              key={t}
              onClick={() => applyTheme(t)}
              className="flex items-center gap-2 px-3 py-1.5 border t-small transition-colors"
              style={{
                color: theme === t ? "var(--accent)" : "var(--fg-1)",
                borderColor: theme === t ? "var(--accent)" : "var(--line)",
                background: theme === t ? "var(--accent-bg)" : "transparent",
              }}
            >
              {t === "dark" ? "◑" : "◐"} {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </section>

      {/* admin links */}
      {sysAdmin && (
        <section className="border border-line" style={{ background: "var(--bg-1)" }}>
          <div className="px-4 py-3 border-b border-line">
            <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Administration</p>
          </div>
          <div className="px-4 py-3">
            <Link
              href="/settings/users"
              className="t-small hover:underline"
              style={{ color: "var(--accent)" }}
            >
              User management →
            </Link>
          </div>
        </section>
      )}

      {/* danger zone */}
      <section className="border border-line" style={{ background: "var(--bg-1)", borderColor: "var(--fail)" }}>
        <div className="px-4 py-3 border-b border-line" style={{ borderColor: "var(--fail)" }}>
          <p className="t-small font-medium" style={{ color: "var(--fail)" }}>Session</p>
        </div>
        <div className="px-4 py-4">
          <button
            onClick={handleSignOut}
            className="t-small px-3 py-1.5 border transition-colors hover:opacity-80"
            style={{ color: "var(--fail)", borderColor: "var(--fail)" }}
          >
            Sign out
          </button>
        </div>
      </section>
    </div>
  );
}

"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const params = useSearchParams();

  const oauthError = params.get("error");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "Invalid credentials");
      }
      const { access_token } = await res.json();
      setToken(access_token);
      router.replace("/overview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  function handleGoogle() {
    window.location.href = `${API}/api/v1/auth/google/authorize`;
  }

  return (
    <div className="w-full max-w-sm p-8 border border-line space-y-6" style={{ background: "var(--bg-1)" }}>
      <p className="font-mono" style={{ fontSize: 20, fontWeight: 300, letterSpacing: "-0.05em", color: "var(--fg-0)" }}>
        dqt
      </p>

      {oauthError && (
        <p className="t-micro px-3 py-2 border" style={{ color: "var(--fail)", borderColor: "var(--fail)", background: "var(--fail-bg)" }}>
          {oauthError === "oauth_failed" ? "Google sign-in failed. Try again." : oauthError === "account_disabled" ? "Account is disabled." : oauthError}
        </p>
      )}

      <button
        onClick={handleGoogle}
        className="w-full flex items-center justify-center gap-2 px-3 py-2.5 t-small border border-line transition-colors hover:opacity-80"
        style={{ color: "var(--fg-0)" }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
        Continue with Google
      </button>

      <div className="flex items-center gap-3">
        <div className="flex-1 border-t border-line" />
        <span className="t-micro" style={{ color: "var(--fg-3)" }}>or</span>
        <div className="flex-1 border-t border-line" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1">
          <label className="t-micro block" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Email</label>
          <input
            type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus
            className="w-full px-3 py-2 border border-line t-small outline-none"
            style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
          />
        </div>
        <div className="space-y-1">
          <label className="t-micro block" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Password</label>
          <input
            type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
            className="w-full px-3 py-2 border border-line t-small outline-none"
            style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
          />
        </div>
        {error && <p className="t-micro" style={{ color: "var(--fail)" }}>{error}</p>}
        <button
          type="submit" disabled={loading}
          className="w-full px-3 py-2 t-small border transition-colors disabled:opacity-40"
          style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)" }}
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="flex items-center justify-center min-h-screen" style={{ background: "var(--bg-0)" }}>
      <Suspense>
        <LoginForm />
      </Suspense>
    </main>
  );
}

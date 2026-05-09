"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken } from "@/lib/auth";

function CallbackHandler() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const token = params.get("token");
    const error = params.get("error");
    if (token) {
      setToken(token);
      router.replace("/overview");
    } else {
      router.replace(`/login?error=${error ?? "oauth_failed"}`);
    }
  }, [params, router]);

  return null;
}

export default function AuthCallbackPage() {
  return (
    <main className="flex items-center justify-center min-h-screen t-small" style={{ background: "var(--bg-0)", color: "var(--fg-2)" }}>
      Signing in…
      <Suspense>
        <CallbackHandler />
      </Suspense>
    </main>
  );
}

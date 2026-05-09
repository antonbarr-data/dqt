"use client";

import { useEffect, useState } from "react";
import { Shield, UserCheck, UserX } from "lucide-react";
import { authHeaders, isSysAdmin } from "@/lib/auth";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

const ROLE_LABELS: Record<string, string> = {
  sysadmin: "Super Admin",
  admin: "Admin",
  editor: "Editor",
  viewer: "Viewer",
};

const ROLE_COLOR: Record<string, string> = {
  sysadmin: "var(--accent)",
  admin: "var(--warn)",
  editor: "var(--fg-1)",
  viewer: "var(--fg-2)",
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (!isSysAdmin()) { router.replace("/overview"); return; }
    fetchUsers();
  }, [router]);

  async function fetchUsers() {
    try {
      const res = await fetch(`${API}/api/v1/admin/users`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to load users");
      setUsers(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  async function setRole(userId: string, role: string) {
    setBusy(userId + role);
    try {
      const res = await fetch(`${API}/api/v1/admin/users/${userId}/role`, {
        method: "PATCH",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      if (!res.ok) throw new Error("Failed to update role");
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role } : u));
    } finally {
      setBusy(null);
    }
  }

  async function toggleActive(userId: string, active: boolean) {
    setBusy(userId + "active");
    try {
      const res = await fetch(`${API}/api/v1/admin/users/${userId}/active?active=${active}`, {
        method: "PATCH",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to update");
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, is_active: active } : u));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      <div className="flex items-center gap-2">
        <Shield size={14} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>User Management</h1>
      </div>
      <p className="t-small" style={{ color: "var(--fg-2)" }}>
        Manage user roles and access. Only Super Admins can promote other Super Admins.
      </p>

      {loading && <p className="t-small" style={{ color: "var(--fg-2)" }}>Loading…</p>}
      {error && <p className="t-small" style={{ color: "var(--fail)" }}>{error}</p>}

      {!loading && !error && (
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr className="border-b border-line" style={{ background: "var(--bg-1)" }}>
              {["Email", "Role", "Status", "Joined", "Actions"].map((h) => (
                <th key={h} className="px-3 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-line last:border-0" style={{ opacity: u.is_active ? 1 : 0.5 }}>
                <td className="px-3 py-2.5">
                  <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{u.email}</span>
                </td>
                <td className="px-3 py-2.5">
                  <span className="t-micro px-2 py-0.5 border" style={{ color: ROLE_COLOR[u.role] ?? "var(--fg-2)", borderColor: ROLE_COLOR[u.role] ?? "var(--line)" }}>
                    {ROLE_LABELS[u.role] ?? u.role}
                  </span>
                </td>
                <td className="px-3 py-2.5 t-small" style={{ color: u.is_active ? "var(--pass)" : "var(--fg-3)" }}>
                  {u.is_active ? "Active" : "Inactive"}
                </td>
                <td className="px-3 py-2.5 t-small font-mono" style={{ color: "var(--fg-2)" }}>
                  {new Date(u.created_at).toLocaleDateString()}
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    {u.role !== "sysadmin" && (
                      <button
                        onClick={() => setRole(u.id, "sysadmin")}
                        disabled={busy === u.id + "sysadmin"}
                        className="flex items-center gap-1 px-2 py-1 t-micro border border-line transition-colors hover:opacity-80 disabled:opacity-40"
                        style={{ color: "var(--accent)" }}
                        title="Promote to Super Admin"
                      >
                        <Shield size={10} strokeWidth={2} />
                        Make Super Admin
                      </button>
                    )}
                    {u.is_active ? (
                      <button
                        onClick={() => toggleActive(u.id, false)}
                        disabled={busy === u.id + "active"}
                        className="flex items-center gap-1 px-2 py-1 t-micro border border-line transition-colors hover:opacity-80 disabled:opacity-40"
                        style={{ color: "var(--fail)" }}
                        title="Deactivate"
                      >
                        <UserX size={10} strokeWidth={2} />
                        Deactivate
                      </button>
                    ) : (
                      <button
                        onClick={() => toggleActive(u.id, true)}
                        disabled={busy === u.id + "active"}
                        className="flex items-center gap-1 px-2 py-1 t-micro border border-line transition-colors hover:opacity-80 disabled:opacity-40"
                        style={{ color: "var(--pass)" }}
                        title="Reactivate"
                      >
                        <UserCheck size={10} strokeWidth={2} />
                        Reactivate
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

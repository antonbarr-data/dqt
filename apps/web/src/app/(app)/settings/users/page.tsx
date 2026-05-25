"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Pencil, Plus, Shield, Trash2, UserCheck, UserX, X } from "lucide-react";
import { authHeaders, isSysAdmin } from "@/lib/auth";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface User {
  id: string;
  email: string;
  name: string | null;
  role: string;
  is_active: boolean;
  oncall_eligible: boolean;
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

const ROLES = ["viewer", "editor", "admin", "sysadmin"];

interface AddUserForm {
  email: string;
  name: string;
  password: string;
  role: string;
  oncall_eligible: boolean;
}

function InlineName({ user, onSave }: { user: User; onSave: (name: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(user.name ?? "");
  const inputRef = useRef<HTMLInputElement>(null);

  function start() { setVal(user.name ?? ""); setEditing(true); setTimeout(() => inputRef.current?.focus(), 0); }
  function save() { setEditing(false); onSave(val); }
  function cancel() { setEditing(false); setVal(user.name ?? ""); }

  if (editing) {
    return (
      <div className="flex items-center gap-1">
        <input
          ref={inputRef}
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") cancel(); }}
          className="px-1.5 py-0.5 t-small border border-line font-mono w-36"
          style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
        />
        <button onClick={save} className="hover:opacity-70"><Check size={11} style={{ color: "var(--pass)" }} /></button>
        <button onClick={cancel} className="hover:opacity-70"><X size={11} style={{ color: "var(--fg-3)" }} /></button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 group">
      <span className="t-small" style={{ color: user.name ? "var(--fg-0)" : "var(--fg-3)" }}>
        {user.name || <span style={{ fontStyle: "italic" }}>—</span>}
      </span>
      <button onClick={start} className="opacity-0 group-hover:opacity-100 transition-opacity">
        <Pencil size={10} style={{ color: "var(--fg-3)" }} />
      </button>
    </div>
  );
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState<AddUserForm>({ email: "", name: "", password: "", role: "viewer", oncall_eligible: false });
  const [addError, setAddError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
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

  async function addUser() {
    setAdding(true);
    setAddError(null);
    try {
      const res = await fetch(`${API}/api/v1/admin/users`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "Failed to create user");
      }
      const created: User = await res.json();
      setUsers((prev) => [...prev, created]);
      setShowAdd(false);
      setForm({ email: "", name: "", password: "", role: "viewer", oncall_eligible: false });
    } catch (e: unknown) {
      setAddError(e instanceof Error ? e.message : "Error");
    } finally {
      setAdding(false);
    }
  }

  async function patchUser(userId: string, patch: Record<string, unknown>) {
    setBusy(userId + Object.keys(patch).join());
    try {
      const res = await fetch(`${API}/api/v1/admin/users/${userId}`, {
        method: "PATCH",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!res.ok) throw new Error("Failed to update user");
      const updated: User = await res.json();
      setUsers((prev) => prev.map((u) => u.id === userId ? updated : u));
    } finally {
      setBusy(null);
    }
  }

  async function deleteUser(userId: string) {
    setBusy(userId + "delete");
    try {
      const res = await fetch(`${API}/api/v1/admin/users/${userId}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to delete user");
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } finally {
      setBusy(null);
      setConfirmDelete(null);
    }
  }

  return (
    <div className="p-6 space-y-5 max-w-5xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield size={14} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
          <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>User Management</h1>
        </div>
        <button
          onClick={() => { setShowAdd(true); setAddError(null); }}
          className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:opacity-80"
          style={{ color: "var(--accent)", borderColor: "var(--accent)" }}
        >
          <Plus size={12} strokeWidth={2} />
          Add User
        </button>
      </div>

      <p className="t-small" style={{ color: "var(--fg-2)" }}>
        Manage user roles, access, and on-call eligibility. Only Super Admins can promote other Super Admins.
      </p>

      {showAdd && (
        <div className="border border-line p-4 space-y-3" style={{ background: "var(--bg-1)" }}>
          <div className="flex items-center justify-between">
            <span className="t-small" style={{ color: "var(--fg-0)" }}>New user</span>
            <button onClick={() => setShowAdd(false)} className="hover:opacity-70">
              <X size={14} style={{ color: "var(--fg-3)" }} />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Full name"
                className="w-full px-2 py-1.5 t-small border border-line"
                style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
              />
            </div>
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="user@example.com"
                className="w-full px-2 py-1.5 t-small border border-line font-mono"
                style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
              />
            </div>
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Password <span style={{ color: "var(--fg-3)" }}>(optional)</span></label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                placeholder="Leave blank for OAuth-only"
                className="w-full px-2 py-1.5 t-small border border-line font-mono"
                style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
              />
            </div>
            <div className="flex items-end gap-4">
              <div>
                <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                  className="px-2 py-1.5 t-small border border-line"
                  style={{ background: "var(--bg-0)", color: "var(--fg-0)", outline: "none" }}
                >
                  {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                </select>
              </div>
              <label className="flex items-center gap-2 cursor-pointer mb-1.5">
                <input
                  type="checkbox"
                  checked={form.oncall_eligible}
                  onChange={(e) => setForm((f) => ({ ...f, oncall_eligible: e.target.checked }))}
                  className="w-3.5 h-3.5"
                />
                <span className="t-small" style={{ color: "var(--fg-1)" }}>On-call eligible</span>
              </label>
            </div>
          </div>
          {addError && <p className="t-micro" style={{ color: "var(--fail)" }}>{addError}</p>}
          <div className="flex gap-2">
            <button
              onClick={addUser}
              disabled={adding || !form.email}
              className="px-3 py-1.5 t-small border transition-colors hover:opacity-80 disabled:opacity-40"
              style={{ color: "var(--accent)", borderColor: "var(--accent)" }}
            >
              {adding ? "Creating..." : "Create User"}
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 t-small border border-line transition-colors hover:opacity-80"
              style={{ color: "var(--fg-2)" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading && <p className="t-small" style={{ color: "var(--fg-2)" }}>Loading...</p>}
      {error && <p className="t-small" style={{ color: "var(--fail)" }}>{error}</p>}

      {!loading && !error && (
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr className="border-b border-line" style={{ background: "var(--bg-1)" }}>
              {["Name", "Email", "Role", "On-call", "Status", "Joined", "Actions"].map((h) => (
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
                  <InlineName user={u} onSave={(name) => patchUser(u.id, { name })} />
                </td>
                <td className="px-3 py-2.5">
                  <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{u.email}</span>
                </td>
                <td className="px-3 py-2.5">
                  <select
                    value={u.role}
                    onChange={(e) => patchUser(u.id, { role: e.target.value })}
                    disabled={u.role === "sysadmin"}
                    className="t-micro px-2 py-0.5 border"
                    style={{
                      color: ROLE_COLOR[u.role] ?? "var(--fg-2)",
                      borderColor: ROLE_COLOR[u.role] ?? "var(--line)",
                      background: "transparent",
                      outline: "none",
                      cursor: u.role === "sysadmin" ? "default" : "pointer",
                    }}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r} style={{ background: "var(--bg-1)", color: "var(--fg-0)" }}>
                        {ROLE_LABELS[r]}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2.5">
                  <button
                    onClick={() => patchUser(u.id, { oncall_eligible: !u.oncall_eligible })}
                    disabled={busy !== null}
                    className="flex items-center gap-1.5 t-micro px-2 py-0.5 border transition-colors hover:opacity-80 disabled:opacity-40"
                    style={{
                      color: u.oncall_eligible ? "var(--pass)" : "var(--fg-3)",
                      borderColor: u.oncall_eligible ? "var(--pass)" : "var(--line)",
                    }}
                  >
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: u.oncall_eligible ? "var(--pass)" : "var(--fg-3)", flexShrink: 0, display: "inline-block" }} />
                    {u.oncall_eligible ? "Eligible" : "Not eligible"}
                  </button>
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
                        onClick={() => patchUser(u.id, { role: "sysadmin" })}
                        disabled={busy !== null}
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
                        onClick={() => patchUser(u.id, { is_active: false })}
                        disabled={busy !== null}
                        className="flex items-center gap-1 px-2 py-1 t-micro border border-line transition-colors hover:opacity-80 disabled:opacity-40"
                        style={{ color: "var(--fail)" }}
                      >
                        <UserX size={10} strokeWidth={2} />
                        Deactivate
                      </button>
                    ) : (
                      <button
                        onClick={() => patchUser(u.id, { is_active: true })}
                        disabled={busy !== null}
                        className="flex items-center gap-1 px-2 py-1 t-micro border border-line transition-colors hover:opacity-80 disabled:opacity-40"
                        style={{ color: "var(--pass)" }}
                      >
                        <UserCheck size={10} strokeWidth={2} />
                        Reactivate
                      </button>
                    )}
                    {confirmDelete === u.id ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => deleteUser(u.id)}
                          disabled={busy === u.id + "delete"}
                          className="px-2 py-1 t-micro border transition-colors hover:opacity-80 disabled:opacity-40"
                          style={{ color: "var(--fail)", borderColor: "var(--fail)" }}
                        >
                          {busy === u.id + "delete" ? "Deleting..." : "Confirm"}
                        </button>
                        <button
                          onClick={() => setConfirmDelete(null)}
                          className="px-2 py-1 t-micro border border-line transition-colors hover:opacity-80"
                          style={{ color: "var(--fg-3)" }}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDelete(u.id)}
                        disabled={busy !== null || u.role === "sysadmin"}
                        className="flex items-center gap-1 px-2 py-1 t-micro border border-line transition-colors hover:opacity-80 disabled:opacity-40"
                        style={{ color: "var(--fg-3)" }}
                        title={u.role === "sysadmin" ? "Cannot delete Super Admin" : "Delete user"}
                      >
                        <Trash2 size={10} strokeWidth={2} />
                        Delete
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

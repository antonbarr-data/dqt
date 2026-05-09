"use client";

import { Sidebar } from "@/components/app-shell/sidebar";
import { Topbar } from "@/components/app-shell/topbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col" style={{ height: "100vh", overflow: "hidden", background: "var(--bg-0)" }}>
      <Topbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto fade-in">
          {children}
        </main>
      </div>
    </div>
  );
}

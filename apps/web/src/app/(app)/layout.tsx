export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen" style={{ background: "var(--bg-0)" }}>{children}</div>;
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

interface IncidentRow {
  id: number;
  dataset_id: string;
  column: string | null;
  detector: string;
  severity: string;
  message: string;
  opened_ago: string;
}

function SeverityDot({ severity }: { severity: string }) {
  const color = severity === "fail" ? "var(--fail)" : "var(--warn)";
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        background: color,
        boxShadow: `0 0 0 2px ${color}28`,
        flexShrink: 0,
      }}
    />
  );
}

export function IncidentTableRow({ inc }: { inc: IncidentRow }) {
  const router = useRouter();
  return (
    <tr
      className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors cursor-pointer"
      style={inc.severity === "fail" ? { background: "var(--fail-bg)" } : undefined}
      onClick={() => router.push(`/incidents/${inc.id}`)}
    >
      <td className="px-3 py-2">
        <SeverityDot severity={inc.severity} />
      </td>
      <td className="px-3 py-2">
        <span
          className="t-micro px-1.5 py-0.5"
          style={{
            background: inc.severity === "fail" ? "var(--fail-bg)" : "rgba(217,181,102,0.12)",
            color: inc.severity === "fail" ? "var(--fail)" : "var(--warn)",
            fontFamily: "var(--font-jetbrains-mono)",
          }}
        >
          {inc.severity}
        </span>
      </td>
      <td className="px-3 py-2">
        <Link
          href={`/datasets/${inc.dataset_id}`}
          className="t-small font-mono hover:underline"
          style={{ color: "var(--fg-0)" }}
          onClick={(e) => e.stopPropagation()}
        >
          {inc.dataset_id}
        </Link>
      </td>
      <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>
        {inc.column ?? "(table)"}
      </td>
      <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-2)" }}>
        {inc.detector}
      </td>
      <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>
        {inc.message}
      </td>
      <td className="px-3 py-2 t-small" style={{ color: "var(--fg-3)" }}>
        {inc.opened_ago}
      </td>
    </tr>
  );
}

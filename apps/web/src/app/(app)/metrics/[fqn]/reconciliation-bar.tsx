"use client";

interface ReconciliationBarProps {
  dataContribution: [number, number];
  businessContribution: [number, number];
  primaryChannel: "data" | "business" | "mixed";
}

export function ReconciliationBar({ dataContribution, businessContribution, primaryChannel }: ReconciliationBarProps) {
  const dataMid = (dataContribution[0] + dataContribution[1]) / 2;
  const bizMid = (businessContribution[0] + businessContribution[1]) / 2;
  const total = dataMid + bizMid || 1;
  const dataPct = Math.round((dataMid / total) * 100);
  const bizPct = 100 - dataPct;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-1">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Movement attribution
        </span>
        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
          primary: {primaryChannel}
        </span>
      </div>
      <div className="flex h-3 border border-line overflow-hidden" style={{ background: "var(--bg-2)" }}>
        <div
          style={{
            width: `${dataPct}%`,
            background: "var(--fail)",
            opacity: primaryChannel === "business" ? 0.4 : 0.8,
            transition: "width 0.4s ease",
          }}
          title={`Data integrity: ${Math.round(dataContribution[0]*100)}-${Math.round(dataContribution[1]*100)}%`}
        />
        <div
          style={{
            width: `${bizPct}%`,
            background: "var(--pass)",
            opacity: primaryChannel === "data" ? 0.4 : 0.8,
            transition: "width 0.4s ease",
          }}
          title={`Business drivers: ${Math.round(businessContribution[0]*100)}-${Math.round(businessContribution[1]*100)}%`}
        />
      </div>
      <div className="flex justify-between mt-1">
        <span className="t-micro" style={{ color: "var(--fail)" }}>
          Data issues {dataPct}% ({Math.round(dataContribution[0]*100)}-{Math.round(dataContribution[1]*100)}%)
        </span>
        <span className="t-micro" style={{ color: "var(--pass)" }}>
          Business drivers {bizPct}% ({Math.round(businessContribution[0]*100)}-{Math.round(businessContribution[1]*100)}%)
        </span>
      </div>
    </div>
  );
}

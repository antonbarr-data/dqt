import { Wizard } from "@/components/connections/wizard";

interface Props {
  params: { engine: string };
}

export default function NewSourcePage({ params }: Props) {
  return (
    <div className="p-6">
      <h1 className="t-h1 mb-6" style={{ color: "var(--fg-0)" }}>Add Connection</h1>
      <Wizard engine={params.engine} />
    </div>
  );
}

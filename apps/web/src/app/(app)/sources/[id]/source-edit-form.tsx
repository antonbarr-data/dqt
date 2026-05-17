"use client";

import { Wizard } from "@/components/connections/wizard";

interface Props {
  engine: string;
  sourceId: string;
  initialValues: Record<string, string>;
}

export function SourceEditForm({ engine, sourceId, initialValues }: Props) {
  return <Wizard engine={engine} sourceId={sourceId} initialValues={initialValues} mode="edit" />;
}

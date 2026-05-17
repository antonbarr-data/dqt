"use client";

import { Wizard } from "@/components/connections/wizard";

interface Props {
  engine: string;
  sourceId: string;
  initialValues: Record<string, string>;
}

export function SourceEditForm({ engine, initialValues }: Props) {
  return <Wizard engine={engine} initialValues={initialValues} mode="edit" />;
}

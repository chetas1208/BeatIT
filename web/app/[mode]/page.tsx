import { notFound } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { isBeatITMode } from "@/lib/product/contracts";

export default async function ProductModePage({ params }: { params: Promise<{ mode: string }> }) {
  const { mode } = await params;
  if (!isBeatITMode(mode)) notFound();
  return <AppShell />;
}

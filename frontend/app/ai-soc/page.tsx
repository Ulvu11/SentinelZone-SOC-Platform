export const dynamic = "force-dynamic";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { AIInvestigation } from "@/components/ai-investigation";
import { EmptyState } from "@/components/empty-state";
export default async function AISocPage({
  searchParams,
}: {
  searchParams: Promise<{ incident?: string }>;
}) {
  const query = await searchParams;
  const incidents = await api.getIncidents();
  if (!incidents.length)
    return <EmptyState title="No investigations available" />;
  const id =
    incidents.find((i) => i.id === query.incident)?.id ?? incidents[0].id;
  const analysis = await api.analyzeWithAI("Analyze incident " + id);
  return (
    <>
      <PageHeader
        eyebrow="Intelligence / Analyst workspace"
        title="AI SOC"
        description="Persisted incident evidence and correlation confidence. An AI inference service is not configured."
      />
      <AIInvestigation
        incidents={incidents}
        initialId={id}
        initialAnalysis={analysis}
      />
    </>
  );
}

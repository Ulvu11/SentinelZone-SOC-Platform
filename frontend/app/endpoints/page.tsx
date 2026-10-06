export const dynamic = "force-dynamic";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { EndpointsTable } from "@/components/endpoints-table";
export default async function EndpointsPage() {
  const endpoints = await api.getEndpoints();
  return (
    <>
      <PageHeader
        eyebrow="Security / Endpoint operations"
        title="Endpoints"
        description="Endpoint inventory, agent health and independent security and hardware risk."
      />
      <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Managed endpoints" value={endpoints.length} />
        <StatCard
          label="Agents online"
          value={endpoints.filter((e) => e.agentStatus === "online").length}
          tone="good"
        />
        <StatCard
          label="Critical security risk"
          value={endpoints.filter((e) => (e.securityRisk ?? -1) >= 80).length}
          tone="critical"
        />
        <StatCard
          label="Hardware attention"
          value={endpoints.filter((e) => (e.hardwareRisk ?? -1) >= 50).length}
          tone="warn"
        />
      </div>
      <EndpointsTable endpoints={endpoints} />
    </>
  );
}

export const dynamic = "force-dynamic";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { IncidentsTable } from "@/components/incidents-table";
import { isActiveIncident } from "@/lib/format";
export default async function IncidentsPage() {
  const incidents = await api.getIncidents();
  return (
    <>
      <PageHeader
        eyebrow="Incident management"
        title="Incidents"
        description={
          incidents.length +
          " total incidents · " +
          incidents.filter((i) => isActiveIncident(i.status)).length +
          " active investigations"
        }
      />
      <IncidentsTable incidents={incidents} />
    </>
  );
}

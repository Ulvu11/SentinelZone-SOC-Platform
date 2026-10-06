export const dynamic = "force-dynamic";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { Panel } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { ActivityTable } from "@/components/activity-table";
export default async function IdentityPage() {
  const events = await api.getIdentityEvents();
  return (
    <>
      <PageHeader
        eyebrow="Monitoring / Identity defense"
        title="Identity"
        description="Authentication activity, privileged access and account abuse."
      />
      <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Failed login events"
          value={events.filter((e) => e.eventType.includes("Failed")).length}
          tone="warn"
        />
        <StatCard
          label="Privileged logins"
          value={
            events.filter((e) => e.eventType.includes("Privileged")).length
          }
        />
        <StatCard
          label="Account lockouts"
          value={events.filter((e) => e.eventType.includes("Lockout")).length}
          tone="critical"
        />
        <StatCard
          label="Suspicious activity"
          value={events.filter((e) => e.severity !== "low").length}
        />
      </div>
      <Panel
        title="Authentication Events"
        subtitle="Investigate source, account and destination together"
      >
        <ActivityTable
          columns={[
            { key: "user", header: "User" },
            { key: "host", header: "Host" },
            { key: "ip", header: "Source IP" },
            { key: "description", header: "Context" },
          ]}
          records={events.map((e) => ({
            id: e.id,
            title: e.eventType,
            timestamp: e.timestamp,
            severity: e.severity,
            fields: {
              user: e.user,
              host: e.host,
              ip: e.sourceIp,
              description: e.description,
            },
          }))}
        />
      </Panel>
    </>
  );
}

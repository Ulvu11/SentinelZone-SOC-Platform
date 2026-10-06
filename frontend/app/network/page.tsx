export const dynamic = "force-dynamic";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { Panel } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { MetricChart } from "@/components/metric-chart";
import { ActivityTable } from "@/components/activity-table";
export default async function NetworkPage() {
  const [alerts, traffic] = await Promise.all([
    api.getNetworkAlerts(),
    api.getNetworkTraffic(),
  ]);
  const rank = (field: "sourceIp" | "destinationIp" | "protocol") =>
    Object.entries(
      alerts.reduce<Record<string, number>>(
        (acc, a) => ({ ...acc, [a[field]]: (acc[a[field]] ?? 0) + 1 }),
        {},
      ),
    ).sort((a, b) => b[1] - a[1]);
  return (
    <>
      <PageHeader
        eyebrow="Monitoring / Network defense"
        title="Network"
        description="Traffic observations, IDS alerts and firewall enforcement."
      />
      <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="IDS alerts"
          value={alerts.filter((a) => a.source.toLowerCase() === "suricata").length}
        />
        <StatCard
          label="Firewall events"
          value="Unavailable"
          hint="pfSense integration is not configured"
        />
        <StatCard
          label="Port scans"
          value={
            alerts.filter((a) => a.title.toLowerCase().includes("scan")).length
          }
          tone="warn"
        />
        <StatCard
          label="Blocked connections"
          value="Unavailable"
          hint="No traffic-counter API is configured"
          tone="warn"
        />
      </div>
      <div className="mb-5 grid gap-4 lg:grid-cols-2">
        <Panel
          title="Traffic Overview"
          subtitle="Traffic-counter telemetry is unavailable; IDS alerts below are real"
        >
          <MetricChart
            label="Inbound Mbps"
            data={traffic.map((t) => ({
              time: t.timestamp,
              value: t.inboundMbps,
            }))}
          />
          <MetricChart
            label="Outbound Mbps"
            color="#22c55e"
            height={75}
            data={traffic.map((t) => ({
              time: t.timestamp,
              value: t.outboundMbps,
            }))}
          />
        </Panel>
        <div className="grid gap-3 sm:grid-cols-3">
          {(["sourceIp", "destinationIp", "protocol"] as const).map(
            (field, index) => (
              <Panel
                key={field}
                title={
                  ["Top Source IPs", "Top Destination IPs", "Protocols"][index]
                }
                subtitle="Observed alerts"
              >
                {rank(field).map(([name, count]) => (
                  <div
                    key={name}
                    className="mb-3 border-b border-soc-line pb-3"
                  >
                    <p className="break-all font-mono text-xs">{name}</p>
                    <div className="mt-2 text-xs text-soc-muted">
                      {count} events
                    </div>
                  </div>
                ))}
              </Panel>
            ),
          )}
        </div>
      </div>
      <Panel
        title="IDS Alerts & Firewall Events"
        subtitle="Search events and use the global time range to focus the observation window"
      >
        <ActivityTable
          columns={[
            { key: "source", header: "Source IP" },
            { key: "destination", header: "Destination" },
            { key: "protocol", header: "Protocol" },
            { key: "sensor", header: "Sensor" },
            { key: "action", header: "Action" },
          ]}
          records={alerts.map((a) => ({
            id: a.id,
            title: a.title,
            timestamp: a.timestamp,
            severity: a.severity,
            fields: {
              source: a.sourceIp,
              destination: a.destinationIp + ":" + a.destinationPort,
              protocol: a.protocol,
              sensor: a.source,
              action: a.action.toUpperCase(),
            },
          }))}
        />
      </Panel>
    </>
  );
}

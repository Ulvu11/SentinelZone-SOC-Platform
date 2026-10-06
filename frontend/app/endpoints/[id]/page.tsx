import { displayMetric } from "@/lib/format";
export const dynamic = "force-dynamic";
import Link from "next/link";
import { api } from "@/lib/api-server";
import { formatTime } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { Panel, DetailList } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { DataTable } from "@/components/data-table";
import { Timeline } from "@/components/timeline";
import { SecurityRiskBadge, RiskScoreBar } from "@/components/risk-badge";
import { EndpointStatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
export default async function EndpointDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [endpoint, incidents, network] = await Promise.all([
    api.getEndpointDetail(id),
    api.getIncidents(),
    api.getNetworkAlerts(),
  ]);
  if (!endpoint)
    return (
      <>
        <Link className="link" href="/endpoints">
          Back to Endpoints
        </Link>
        <EmptyState
          title="Endpoint not found"
          description="This endpoint ID is not in the current inventory."
        />
      </>
    );
  const related = incidents.filter(
    (i) => i.affectedAsset === endpoint.hostname,
  );
  const details = await Promise.all(
    related.map((i) => api.getIncidentDetail(i.id)),
  );
  const timeline = details.flatMap((i) => i?.timeline ?? []);
  const connections = network.filter(
    (n) => n.sourceIp === endpoint.ip || n.destinationIp === endpoint.ip,
  );
  return (
    <div className="space-y-5">
      <nav aria-label="Breadcrumb" className="text-xs text-soc-muted">
        <Link className="link" href="/endpoints">
          Endpoints
        </Link>{" "}
        / {endpoint.hostname}
      </nav>
      <PageHeader
        eyebrow="Endpoint telemetry"
        title={endpoint.hostname}
        description={endpoint.ip + " · " + endpoint.user + " · " + endpoint.os}
        actions={<EndpointStatusBadge status={endpoint.status} />}
      />
      <div className="flex flex-wrap gap-5 text-xs text-soc-muted">
        <span>
          Agent:{" "}
          <strong className="text-soc-good">
            {endpoint.agentStatus.toUpperCase()}
          </strong>
        </span>
        <span>Last seen: {formatTime(endpoint.lastSeen)}</span>
        <span>User idle: {displayMetric(endpoint.userIdleMinutes, " min")}</span>
        <span>Agent ID: {endpoint.agentId}</span>
        <span>Version: {endpoint.agentVersion}</span>
      </div>
      <nav
        aria-label="Endpoint sections"
        className="flex flex-wrap gap-2 border-b border-soc-line pb-3"
      >
        {[
          "Overview",
          "Processes",
          "Telemetry",
          "Network",
          "Security",
          "Timeline",
        ].map((label) => (
          <a className="button" key={label} href={"#" + label.toLowerCase()}>
            {label}
          </a>
        ))}
      </nav>
      <div id="overview" className="grid gap-4 lg:grid-cols-2">
        <Panel
          title="Security Risk"
          subtitle="Behavior, execution and threat indicators"
        >
          <RiskScoreBar label="Security risk" score={endpoint.securityRisk} />
          <div className="mt-4">
            <DetailList items={endpoint.securityRiskReasons} />
          </div>
        </Panel>
        <Panel
          title="Resource impact"
          subtitle="Process resource use, independent of security risk"
        >
          <RiskScoreBar label="Resource impact" score={endpoint.hardwareRisk} />
          <div className="mt-4">
            <DetailList items={endpoint.hardwareRiskReasons} />
          </div>
        </Panel>
      </div>
      <Panel
        id="telemetry"
        title="Telemetry"
        subtitle={"Latest agent observation · " + formatTime(endpoint.lastSeen)}
      >
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          {[
            ["CPU usage", displayMetric(endpoint.cpu, "%")],
            ["GPU usage", displayMetric(endpoint.gpu, "%")],
            ["RAM usage", displayMetric(endpoint.ram, "%")],
            ["CPU temperature", displayMetric(endpoint.cpuTemperature, " °C")],
            [
              "GPU temperature",
              endpoint.gpuTemperature
                ? displayMetric(endpoint.gpuTemperature, " °C")
                : "Not available",
            ],
            ["Disk temperature", displayMetric(endpoint.diskTemperature, " °C")],
            ["Fan status", endpoint.fanStatus],
            ["User idle", displayMetric(endpoint.userIdleMinutes, " min")],
          ].map(([label, value]) => (
            <StatCard key={label} label={String(label)} value={value} />
          ))}
        </div>
      </Panel>
      <Panel title="Sensor availability" subtitle="Unknown readings remain unavailable">
        <div className="grid gap-2 md:grid-cols-2">{endpoint.sensorAvailability?.map(s=><div key={s.name} className="rounded border border-soc-line p-3 text-xs"><strong>{s.name}: {s.status}</strong><p className="mt-1 text-soc-muted">{s.detail}</p></div>)}</div>
        <DetailList items={endpoint.unknownData??[]} />
      </Panel>
      <Panel title="Endpoint network evidence" subtitle="Read-only connection observations from CryptoGuard">
        <DataTable data={endpoint.networkConnections??[]} keyExtractor={(c)=>`${c.local_address}:${c.local_port}-${c.remote_address}:${c.remote_port}`} columns={[
          {key:"local",header:"Local",render:c=>`${c.local_address}:${c.local_port}`},
          {key:"remote",header:"Remote",render:c=>`${c.remote_address}:${c.remote_port}`},
          {key:"state",header:"State",render:c=>c.state},
          {key:"owner",header:"Ownership",render:c=>c.owner_status},
        ]}/>
      </Panel>
      <Panel title="Persistence observations" subtitle="An observed entry is not a maliciousness verdict">
        <DataTable data={endpoint.persistenceObservations??[]} keyExtractor={(p)=>`${p.source}-${p.location}-${p.executable}`} columns={[
          {key:"source",header:"Source",render:p=>p.source},
          {key:"location",header:"Location",render:p=><span className="break-all">{p.location}</span>},
          {key:"executable",header:"Executable",render:p=><span className="break-all">{p.executable??"Unavailable"}</span>},
          {key:"status",header:"Status",render:p=>p.status},
        ]}/>
      </Panel>
      <Panel
        id="processes"
        title="Processes"
        subtitle="Executable provenance and resource utilization"
      >
        <DataTable
          data={endpoint.processes}
          keyExtractor={(p) => String(p.pid)}
          columns={[
            {
              key: "name",
              header: "Process",
              render: (p) => <span className="font-mono">{p.name}</span>,
            },
            { key: "pid", header: "PID", render: (p) => p.pid },
            {
              key: "parent",
              header: "Parent process",
              render: (p) => p.parentProcess ?? "Not captured",
            },
            { key: "cpu", header: "CPU", render: (p) => displayMetric(p.cpu, "%") },
            { key: "gpu", header: "GPU", render: (p) => displayMetric(p.gpu, "%") },
            {
              key: "path",
              header: "Executable path",
              render: (p) => (
                <span className="block min-w-64 break-all font-mono text-xs">
                  {p.path}
                </span>
              ),
            },
            {
              key: "signed",
              header: "Signature",
              render: (p) => (
                <span
                  className={p.signed ? "text-soc-good" : "text-soc-danger"}
                >
                  {p.signed === null ? "Unknown / not Authenticode" : p.signed ? "Signed" : "Unsigned"}
                </span>
              ),
            },
            {
              key: "network",
              header: "Network activity",
              render: (p) => p.networkActivity,
            },
            {
              key: "risk",
              header: "Risk",
              render: (p) => <SecurityRiskBadge score={p.risk} />,
            },
          ]}
        />
      </Panel>
      <Panel id="network" title="Network" subtitle={endpoint.networkActivity}>
        <DataTable
          data={connections}
          keyExtractor={(n) => n.id}
          columns={[
            { key: "event", header: "Event", render: (n) => n.title },
            { key: "source", header: "Source IP", render: (n) => n.sourceIp },
            {
              key: "destination",
              header: "Destination",
              render: (n) => n.destinationIp + ":" + n.destinationPort,
            },
            { key: "protocol", header: "Protocol", render: (n) => n.protocol },
            { key: "action", header: "Action", render: (n) => n.action },
          ]}
        />
        <Link className="link mt-3 inline-block text-xs" href="/network">
          Open network monitoring →
        </Link>
      </Panel>
      <div className="grid items-start gap-4 lg:grid-cols-2">
        <Panel
          id="security"
          title="Security"
          subtitle="Correlated investigations"
        >
          {related.length ? (
            related.map((i) => (
              <Link
                key={i.id}
                className="block rounded-md border border-soc-line p-3 text-sm hover:bg-soc-surface"
                href={"/incidents/" + i.id}
              >
                <span className="link">{i.id}</span> · {i.title}
                <div className="mt-1 text-xs text-soc-muted">
                  {i.detectionSources.join(" · ")}
                </div>
              </Link>
            ))
          ) : (
            <EmptyState
              title="No correlated incidents"
              description="No incident in the current dataset references this endpoint."
            />
          )}
        </Panel>
        <Panel id="timeline" title="Timeline">
          <Timeline
            events={
              timeline.length
                ? timeline
                : [
                    {
                      id: endpoint.id + "-seen",
                      timestamp: endpoint.lastSeen,
                      title: "Agent telemetry received",
                      description:
                        "Inventory and resource measurements updated.",
                      category: "info",
                    },
                  ]
            }
          />
        </Panel>
      </div>
    </div>
  );
}

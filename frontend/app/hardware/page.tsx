import { displayMetric } from "@/lib/format";
import { countAboveThreshold } from "@/lib/telemetry-metrics";
export const dynamic = "force-dynamic";
import Link from "next/link";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { Panel, DetailList } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { EndpointsTable } from "@/components/endpoints-table";
import { RiskScoreBar } from "@/components/risk-badge";
export default async function HardwarePage() {
  const endpoints = await api.getEndpoints();
  const gpuObserved = endpoints.filter((e) => e.gpu !== null);
  const details = (
    await Promise.all(
      endpoints
        .filter((e) => (e.hardwareRisk ?? -1) >= 50)
        .map((e) => api.getEndpointDetail(e.id)),
    )
  ).filter((e) => e !== null);
  return (
    <>
      <PageHeader
        eyebrow="Security / Hardware intelligence"
        title="Hardware / CryptoGuard"
        description="Separate malicious resource use from legitimate workloads and thermal stress."
      />
      <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Monitored systems" value={endpoints.length} />
        <StatCard
          label="Hardware warnings"
          value={details.length}
          tone="warn"
        />
        <StatCard
          label="Security escalations"
          value={endpoints.filter((e) => (e.securityRisk ?? -1) >= 80).length}
          tone="critical"
        />
        <StatCard
          label="GPU above 90%"
          value={countAboveThreshold(endpoints.map((e) => e.gpu), 90) ?? "Unavailable"}
          hint={gpuObserved.length ? `${gpuObserved.length} of ${endpoints.length} systems report GPU utilization` : "No supported GPU utilization sensor reported"}
        />
      </div>
      <div className="mb-5 grid gap-4 lg:grid-cols-2">
        {details.map((e) => (
          <Panel
            key={e.id}
            title={e.hostname}
            subtitle={e.user + " · " + e.ip}
            action={
              <Link className="link text-xs" href={"/endpoints/" + e.id}>
                Telemetry →
              </Link>
            }
          >
            <div className="space-y-3">
              <RiskScoreBar label="Security risk" score={e.securityRisk} />
              <RiskScoreBar label="Resource impact" score={e.hardwareRisk} />
              <p className="text-xs text-soc-muted">
                GPU {displayMetric(e.gpu,"%")} · GPU {displayMetric(e.gpuTemperature," °C")} · idle{" "}
                {displayMetric(e.userIdleMinutes," min")}
              </p>
              <DetailList
                items={[
                  ...e.hardwareRiskReasons,
                  ...e.securityRiskReasons.slice(0, 2),
                ]}
              />
            </div>
          </Panel>
        ))}
      </div>
      <EndpointsTable endpoints={endpoints} />
    </>
  );
}

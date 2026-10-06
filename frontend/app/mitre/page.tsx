export const dynamic = "force-dynamic";
import Link from "next/link";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { Panel } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { DataTable } from "@/components/data-table";
export default async function MitrePage() {
  const techniques = await api.getMitreTechniques();
  if (!techniques.length) return <Panel title="MITRE mapping" subtitle="This capability has no configured backend API. No sample data is displayed.">{null}</Panel>;
  return (
    <>
      <PageHeader
        eyebrow="Intelligence / Detection engineering"
        title="MITRE ATT&CK"
        description="Coverage of tracked techniques, supporting sensors and correlated incidents."
      />
      <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Tracked techniques" value={techniques.length} />
        <StatCard
          label="Average coverage"
          value={
            (techniques.length
              ? Math.round(
                  techniques.reduce((s, t) => s + t.coverage, 0) /
                    techniques.length,
                )
              : 0) + "%"
          }
        />
        <StatCard
          label="Coverage gaps"
          value={techniques.filter((t) => t.coverage === 0).length}
          tone="warn"
        />
        <StatCard
          label="Detection sources"
          value={new Set(techniques.flatMap((t) => t.detectionSources)).size}
        />
      </div>
      <Panel
        title="Technique Coverage"
        subtitle="Coverage values are local detection assessments, not the entire ATT&CK catalog"
      >
        <DataTable
          data={techniques}
          keyExtractor={(t) => t.id}
          columns={[
            {
              key: "technique",
              header: "Technique",
              render: (t) => (
                <div id={t.id} className="min-w-52 scroll-mt-24">
                  <span className="font-mono text-xs text-soc-accent">
                    {t.id}
                  </span>
                  <p className="font-medium">{t.name}</p>
                  <p className="mt-1 text-xs text-soc-muted">{t.description}</p>
                </div>
              ),
            },
            { key: "tactic", header: "Tactic", render: (t) => t.tactic },
            {
              key: "coverage",
              header: "Coverage",
              render: (t) => (
                <div className="min-w-28">
                  <span
                    className={t.coverage ? "text-soc-good" : "text-soc-warn"}
                  >
                    {t.coverage}% {t.coverage === 0 ? "GAP" : ""}
                  </span>
                  <progress
                    className="mt-2 block h-1.5 w-full accent-soc-accent"
                    value={t.coverage}
                    max={100}
                    aria-label={t.id + " coverage"}
                  />
                </div>
              ),
            },
            {
              key: "incidents",
              header: "Associated incidents",
              render: (t) => (
                <div className="flex flex-wrap gap-2">
                  {t.incidentIds.length ? (
                    t.incidentIds.map((id) => (
                      <Link
                        key={id}
                        className="link text-xs"
                        href={"/incidents/" + id}
                      >
                        {id}
                      </Link>
                    ))
                  ) : (
                    <span className="text-xs text-soc-muted">
                      No correlated incidents
                    </span>
                  )}
                </div>
              ),
            },
            {
              key: "sources",
              header: "Detection sources",
              render: (t) =>
                t.detectionSources.join(", ") || "No active detection",
            },
          ]}
        />
      </Panel>
    </>
  );
}

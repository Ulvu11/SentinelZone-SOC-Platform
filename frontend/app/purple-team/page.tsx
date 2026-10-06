export const dynamic = "force-dynamic";
import Link from "next/link";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { Panel } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { formatTime } from "@/lib/format";
import { EmptyState } from "@/components/empty-state";
export default async function PurpleTeamPage() {
  const campaigns = await api.getEmulationCampaigns();
  if (!campaigns.length) return <Panel title="Purple-team campaigns" subtitle="This capability has no configured backend API. No sample data is displayed.">{null}</Panel>;
  return (
    <>
      <PageHeader
        eyebrow="Intelligence / Adversary validation"
        title="Purple Team"
        description="Campaign results and actionable detection gaps."
      />
      <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Campaigns" value={campaigns.length} />
        <StatCard
          label="Techniques tested"
          value={new Set(campaigns.flatMap((c) => c.techniques)).size}
        />
        <StatCard
          label="Detected techniques"
          value={new Set(campaigns.flatMap((c) => c.detectedTechniques)).size}
          tone="good"
        />
        <StatCard
          label="Detection gaps"
          value={new Set(campaigns.flatMap((c) => c.missedTechniques)).size}
          tone="warn"
        />
      </div>
      {!campaigns.length && <EmptyState title="No campaigns available" />}
      {campaigns.map((c) => (
        <Panel
          key={c.id}
          title={c.name}
          subtitle={c.id + " · " + formatTime(c.startedAt)}
          action={<span className="badge uppercase">{c.status}</span>}
        >
          <div className="grid gap-4 md:grid-cols-3">
            {[
              ["Techniques Tested", c.techniques],
              ["Detected Techniques", c.detectedTechniques],
              ["Detection Gaps", c.missedTechniques],
            ].map(([label, ids]) => (
              <div
                key={String(label)}
                className="rounded-md border border-soc-line bg-soc-surface p-4"
              >
                <h3 className="mb-3 text-sm font-medium">{label}</h3>
                <div className="flex flex-wrap gap-2">
                  {(ids as string[]).map((id) => (
                    <Link key={id} className="badge link" href={"/mitre#" + id}>
                      {id}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm text-soc-muted">
            Next review: improve command interpreter telemetry for the missed
            technique, tune correlation, and repeat the campaign after
            validation.
          </p>
        </Panel>
      ))}
    </>
  );
}

export const dynamic = "force-dynamic";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { Panel } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { DataTable } from "@/components/data-table";
import { formatTime } from "@/lib/format";
export default async function BackupPage() {
  const systems = await api.getBackupStatus();
  if (!systems.length) return <Panel title="Backup status" subtitle="This capability has no configured backend API. No sample data is displayed.">{null}</Panel>;
  return (
    <>
      <PageHeader
        eyebrow="Operations / Recovery readiness"
        title="Backup"
        description="Protection status and restore readiness of critical systems."
      />
      <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Protected systems"
          value={systems.filter((s) => s.protected).length}
        />
        <StatCard
          label="Healthy backups"
          value={systems.filter((s) => s.status === "healthy").length}
          tone="good"
        />
        <StatCard
          label="Restore ready"
          value={systems.filter((s) => s.restoreReady).length}
        />
        <StatCard
          label="Needs attention"
          value={systems.filter((s) => s.status !== "healthy").length}
          tone="warn"
        />
      </div>
      <Panel title="Protected Systems">
        <DataTable
          data={systems}
          keyExtractor={(s) => s.id}
          columns={[
            {
              key: "system",
              header: "System",
              render: (s) => <strong>{s.system}</strong>,
            },
            {
              key: "status",
              header: "Backup status",
              render: (s) => (
                <span
                  className={
                    "badge uppercase " +
                    (s.status === "healthy" ? "text-soc-good" : "text-soc-warn")
                  }
                >
                  {s.status}
                </span>
              ),
            },
            {
              key: "last",
              header: "Last successful backup",
              render: (s) => formatTime(s.lastBackup),
            },
            {
              key: "restore",
              header: "Restore readiness",
              render: (s) => (s.restoreReady ? "Ready" : "Action required"),
            },
            {
              key: "immutable",
              header: "Immutable",
              render: (s) => (s.immutable ? "Enabled" : "Not enabled"),
            },
            {
              key: "protected",
              header: "Protection",
              render: (s) => (s.protected ? "Protected" : "Unprotected"),
            },
          ]}
        />
      </Panel>
      <div className="mt-4">
        <Panel title="Recovery Follow-up">
          {systems
            .filter((s) => s.status !== "healthy" || !s.immutable)
            .map((s) => (
              <p key={s.id} className="text-sm text-soc-muted">
                <strong className="text-soc-warn">{s.system}</strong> — review
                the backup schedule
                {!s.immutable ? " and enable immutable storage" : ""}. Validate
                recovery in an isolated environment.
              </p>
            ))}
        </Panel>
      </div>
    </>
  );
}

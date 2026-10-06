export const dynamic = "force-dynamic";
import Link from "next/link";
import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { Panel } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { SeverityBadge } from "@/components/severity-badge";
import { formatTime } from "@/lib/format";
import { EmptyState } from "@/components/empty-state";
export default async function HoneypotsPage() {
  const [metrics, sessions] = await Promise.all([
    api.getHoneypotMetrics(),
    api.getHoneypotSessions(),
  ]);
  return (
    <>
      <PageHeader
        eyebrow="Monitoring / Deception"
        title="Honeypots"
        description="Cowrie SSH activity and captured attacker sessions from isolated decoys."
      />
      <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-6">
        {[
          ["Attacks today", metrics.attacksToday],
          ["Unique attackers", metrics.uniqueAttackers],
          ["SSH attempts", metrics.sshAttempts],
          ["Commands executed", metrics.commandsExecuted],
          ["Files downloaded", metrics.filesDownloaded],
          ["Decoy logins", metrics.successfulDecoyLogins],
        ].map(([label, value]) => (
          <StatCard key={label} label={String(label)} value={value} />
        ))}
      </div>
      <Panel
        title="Recent Sessions"
        subtitle="Detailed captured session sample; counters above cover the full daily aggregate"
      >
        {sessions.length ? (
          sessions.map((s) => (
            <details
              key={s.id}
              open
              className="rounded-lg border border-soc-line bg-soc-surface p-4"
            >
              <summary className="text-sm">
                <span className="font-mono">{s.sourceIp}</span> · {s.username} ·{" "}
                {s.durationSeconds}s <SeverityBadge severity={s.severity} />
              </summary>
              <p className="my-3 text-xs text-soc-muted">
                {s.id} · {formatTime(s.startedAt)}
              </p>
              <div className="grid gap-4 lg:grid-cols-2">
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase text-soc-muted">
                    Commands Executed
                  </h3>
                  <ol className="space-y-2 rounded-md bg-soc-bg p-3 font-mono text-xs">
                    {s.commands.map((c) => (
                      <li key={c.timestamp} className="break-all">
                        <span className="mr-3 text-soc-muted">
                          {c.timestamp}
                        </span>
                        {c.command}
                      </li>
                    ))}
                  </ol>
                </div>
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase text-soc-muted">
                    Files Downloaded
                  </h3>
                  {s.downloadedFiles.map((f) => (
                    <p key={f} className="mb-2 font-mono text-sm">
                      {f} <span className="badge">Captured artifact</span>
                    </p>
                  ))}
                  <Link href="/incidents/INC-0041" className="link text-sm">
                    Review SSH investigation →
                  </Link>
                </div>
              </div>
            </details>
          ))
        ) : (
          <EmptyState title="No sessions captured" />
        )}
      </Panel>
    </>
  );
}

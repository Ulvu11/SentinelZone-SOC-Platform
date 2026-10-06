export const dynamic = "force-dynamic";
import { backend } from "@/lib/sentinelzone-backend";
import { PageHeader } from "@/components/page-header";
import { SettingsWorkspace } from "@/components/settings-workspace";
export default async function SettingsPage() {
  const health = await backend<{connectors:Record<string,{status:string}>}>("/v1/telemetry-health");
  return (
    <>
      <PageHeader
        eyebrow="Operations / Workspace configuration"
        title="Settings"
        description="Workspace preferences, appearance, integrations and access reference."
      />
      <SettingsWorkspace health={health} />
    </>
  );
}

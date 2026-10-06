import { PageHeader } from "@/components/page-header";
import { ThreatHuntWorkspace } from "@/components/threat-hunt-workspace";
export default function ThreatHuntingPage() {
  return (
    <>
      <PageHeader
        eyebrow="Intelligence / Proactive investigation"
        title="Threat Hunting"
        description="Pivot from an indicator to the supporting SOC evidence."
      />
      <ThreatHuntWorkspace />
    </>
  );
}

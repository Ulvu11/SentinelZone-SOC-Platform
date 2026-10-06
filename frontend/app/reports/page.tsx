import { PageHeader } from "@/components/page-header";
import { SocReportWorkspace } from "@/components/soc-report-workspace";

export default function ReportsPage() {
  return <div className="soc-report-page">
    <PageHeader eyebrow="Operations / Security reporting" title="Reports" description="SOC summary from persisted SentinelZone observations. Select a time range, review availability and export the same report." />
    <SocReportWorkspace />
  </div>;
}

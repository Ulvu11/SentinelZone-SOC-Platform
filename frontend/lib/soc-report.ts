export interface ReportAlert {
  id: string; observed_at: string; severity: string; source: string; title: string;
  host: string | null; source_ip: string | null; destination_ip: string | null;
}
type Availability = "available" | "unavailable" | "not_configured";
type SourceSummary = { status: Availability; event_count: number | null; source: string; event_types: Record<string, number> };
export interface SocReport {
  schema_version: string; title: string; tenant: string; generated_at: string; scope: string;
  time_range: { from: string; to: string; boundary: string }; data_complete: boolean;
  alerts: { status: Availability; count: number | null; severity_distribution: Record<string, number>; source_distribution: Record<string, number>; latest: ReportAlert[]; high_priority: ReportAlert[]; list_limit: number };
  incidents: { status: Availability; count: number | null; open_count: number | null; status_distribution: Record<string, number>; list_limit: number; list_truncated: boolean;
    items: { id: string; title: string; severity: string; status: string; opened_at: string; host: string | null; owner: string | null }[] };
  identity: { status: Availability; event_count: number | null; severity_distribution: Record<string, number>; method: string };
  network: SourceSummary; honeypots: SourceSummary;
  cryptoguard: { status: Availability; agents_with_telemetry: number | null; scope: string; list_truncated: boolean;
    items: { agent_id: string; hostname: string | null; platform: string; observed_at: string; agent_version: string | null; cpu_percent: number | null; gpu_percent: number | null; ram_percent: number | null; temperature_c: number | null; security_risk: number | null; resource_impact: number | null; assessment_source: string }[] };
  connectors: Record<string, { status: string; last_success_at: string | null; last_event_at: string | null }>;
}
export const reportValue = (value: string | number | null | undefined): string => value == null ? "Unavailable" : String(value);
export const availabilityLabel = (value: Availability) => value === "not_configured" ? "Not configured" : value === "unavailable" ? "Unavailable" : "Available";
export type ReportSection = { title: string; description?: string; headers: string[]; rows: string[][] };
export function reportSections(r: SocReport): ReportSection[] {
  const distribution = (title: string, data: Record<string, number>): ReportSection => ({ title, headers: ["Category", "Count"], rows: Object.keys(data).sort().map(key => [key, String(data[key])]) });
  const alerts = (title: string, rows: ReportAlert[]): ReportSection => ({ title, description: `Up to ${r.alerts.list_limit} most recent matching records.`, headers: ["Observed (UTC)", "Severity", "Source", "Title", "Host", "Source IP", "Destination IP", "Event ID"], rows: rows.map(e => [e.observed_at, e.severity, e.source, e.title, reportValue(e.host), reportValue(e.source_ip), reportValue(e.destination_ip), e.id]) });
  return [
    { title: "Report metadata", headers: ["Field", "Value"], rows: [["Tenant", r.tenant], ["Generated at (UTC)", r.generated_at], ["From (UTC)", r.time_range.from], ["To (UTC)", r.time_range.to], ["Range boundary", r.time_range.boundary], ["Scope", r.scope], ["All connectors healthy", r.data_complete ? "Yes" : "No — inspect connector availability"]] },
    { title: "SOC summary", headers: ["Metric", "Value", "Availability"], rows: [["Alert count", reportValue(r.alerts.count), availabilityLabel(r.alerts.status)], ["Incident count", reportValue(r.incidents.count), availabilityLabel(r.incidents.status)], ["Open incidents", reportValue(r.incidents.open_count), availabilityLabel(r.incidents.status)]] },
    distribution("Alert severity distribution", r.alerts.severity_distribution), distribution("Alert source distribution", r.alerts.source_distribution),
    alerts("Latest alerts", r.alerts.latest), alerts("High-priority alerts", r.alerts.high_priority),
    { title: "Incident list", description: r.incidents.list_truncated ? `Showing ${r.incidents.items.length} of ${r.incidents.count}; list truncated, aggregate counts are complete.` : "Incidents opened in the selected range; statuses at report generation.", headers: ["ID", "Opened (UTC)", "Severity", "Status", "Title", "Host", "Owner"], rows: r.incidents.items.map(i => [i.id, i.opened_at, i.severity, i.status, i.title, reportValue(i.host), i.owner ?? "Unassigned"]) },
    { title: "Identity summary", description: r.identity.method, headers: ["Availability", "Matching events"], rows: [[availabilityLabel(r.identity.status), reportValue(r.identity.event_count)]] },
    distribution("Identity severity distribution", r.identity.severity_distribution),
    ...([ ["Network summary", r.network], ["Honeypot summary", r.honeypots] ] as const).map(([title, source]) => ({ title, description: "Persisted source events in the selected range; event types include non-alert observations.", headers: ["Availability", "Source", "Event count"], rows: [[availabilityLabel(source.status), source.source, reportValue(source.event_count)]] })),
    ...(r.network.status === "available" ? [distribution("Network event types", r.network.event_types)] : []),
    ...(r.honeypots.status === "available" ? [distribution("Honeypot event types", r.honeypots.event_types)] : []),
    { title: "CryptoGuard summary", description: r.cryptoguard.scope, headers: ["Availability", "Agents with telemetry", "List truncated"], rows: [[availabilityLabel(r.cryptoguard.status), reportValue(r.cryptoguard.agents_with_telemetry), r.cryptoguard.list_truncated ? "Yes" : "No"]] },
    ...(r.cryptoguard.items.length ? [{ title: "CryptoGuard telemetry", headers: ["Agent ID", "Hostname", "Platform", "Observed (UTC)", "Version", "CPU %", "GPU %", "RAM %", "Temperature °C", "Security risk", "Resource impact", "Assessment source"], rows: r.cryptoguard.items.map(a => [a.agent_id, reportValue(a.hostname), a.platform, a.observed_at, reportValue(a.agent_version), ...[a.cpu_percent, a.gpu_percent, a.ram_percent, a.temperature_c, a.security_risk, a.resource_impact].map(reportValue), a.assessment_source]) }] : []),
    { title: "Connector availability at generation", headers: ["Connector", "Status", "Last success (UTC)", "Last event (UTC)"], rows: Object.entries(r.connectors).map(([name, s]) => [name, s.status, reportValue(s.last_success_at), reportValue(s.last_event_at)]) },
  ];
}
// Event titles and other cells may contain untrusted text supplied by a monitored host.
export function csvCell(value: string): string {
  const safe = /^[\s\u0000-\u001f]*[=+@-]/.test(value) || /^[\t\r\n]/.test(value) ? "'" + value : value;
  return '"' + safe.replaceAll('"', '""') + '"';
}
export function reportCsv(report: SocReport): string {
  const rows: string[][] = [["SOC Summary Report"]];
  for (const s of reportSections(report)) {
    rows.push([], [s.title]);
    if (s.description) rows.push([s.description]);
    rows.push(s.headers, ...(s.rows.length ? s.rows : [["Unavailable — no matching records in the selected range"]]));
  }
  return "\ufeff" + rows.map(row => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
}

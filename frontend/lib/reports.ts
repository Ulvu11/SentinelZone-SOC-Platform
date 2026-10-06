import type {
  ReportTemplate,
  Incident,
  Endpoint,
  NetworkAlert,
  MITRETechnique,
  OverviewMetrics,
} from "@/types";
export interface ReportDocument {
  id: string;
  title: string;
  description: string;
  sections: { title: string; headers: string[]; rows: string[][] }[];
}
export function createReport(
  template: ReportTemplate,
  data: {
    overview: OverviewMetrics;
    incidents: Incident[];
    endpoints: Endpoint[];
    network: NetworkAlert[];
    techniques: MITRETechnique[];
  },
): ReportDocument {
  const { overview, incidents, endpoints, network, techniques } = data;
  const endpointSection = {
    title: "Endpoint risk inventory",
    headers: [
      "Hostname",
      "IP",
      "User",
      "Security risk",
      "Hardware risk",
      "Agent",
      "Last seen",
    ],
    rows: endpoints.map((e) => [
      e.hostname,
      e.ip,
      e.user,
      String(e.securityRisk),
      String(e.hardwareRisk),
      e.agentStatus,
      e.lastSeen,
    ]),
  };
  const sections = template.name.includes("Executive")
    ? [
        {
          title: "Security posture",
          headers: ["Metric", "Value"],
          rows: [
            ["Security score", String(overview.securityScore)],
            ["Protected endpoints", String(overview.totalEndpoints)],
            ["Open incidents", String(overview.activeIncidents)],
            ["Critical incidents", String(overview.criticalIncidents)],
            ["Alerts", String(overview.alertsToday)],
          ],
        },
        {
          title: "Priority investigations",
          headers: ["Incident", "Title", "Severity", "Status", "Asset"],
          rows: incidents
            .filter((i) => i.status === "open" || i.status === "investigating")
            .map((i) => [i.id, i.title, i.severity, i.status, i.affectedAsset]),
        },
      ]
    : template.name.includes("Incident")
      ? [
          {
            title: "Incident register",
            headers: [
              "ID",
              "Title",
              "Severity",
              "Status",
              "Asset",
              "User",
              "Source IP",
              "Sources",
              "MITRE",
              "Confidence",
              "Analyst",
              "Created",
            ],
            rows: incidents.map((i) => [
              i.id,
              i.title,
              i.severity,
              i.status,
              i.affectedAsset,
              i.affectedUser,
              i.sourceIp,
              i.detectionSources.join(", "),
              i.mitreTechniques.join(", "),
              i.confidence + "%",
              i.assignedTo ?? "Unassigned",
              i.createdAt,
            ]),
          },
        ]
      : template.name.includes("Network")
        ? [
            {
              title: "Network detections",
              headers: [
                "ID",
                "Event",
                "Source",
                "Destination",
                "Protocol",
                "Action",
              ],
              rows: network.map((n) => [
                n.id,
                n.title,
                n.sourceIp,
                n.destinationIp,
                n.protocol,
                n.action,
              ]),
            },
          ]
        : template.name.includes("MITRE")
          ? [
              {
                title: "Tracked detection coverage",
                headers: [
                  "Technique",
                  "Name",
                  "Tactic",
                  "Coverage",
                  "Incidents",
                  "Sources",
                ],
                rows: techniques.map((t) => [
                  t.id,
                  t.name,
                  t.tactic,
                  t.coverage + "%",
                  t.incidentIds.join(", "),
                  t.detectionSources.join(", "),
                ]),
              },
            ]
          : template.name.includes("CryptoGuard")
            ? [
                endpointSection,
                {
                  title: "Resource telemetry",
                  headers: ["Hostname", "CPU %", "GPU %", "RAM %"],
                  rows: endpoints.map((e) => [
                    e.hostname,
                    String(e.cpu),
                    String(e.gpu),
                    String(e.ram),
                  ]),
                },
              ]
            : [endpointSection];
  return {
    id: template.id,
    title: template.name,
    description: template.description,
    sections,
  };
}
export function reportMarkdown(report: ReportDocument) {
  const escape = (value: string) =>
    value.replaceAll("|", "\\|").replaceAll("\n", " ");
  return (
    "# " +
    report.title +
    "\n\n" +
    report.description +
    "\n\nScope: current SOC observation snapshot. Security and hardware scores are independent.\n\n" +
    report.sections
      .map(
        (s) =>
          "## " +
          s.title +
          "\n\n| " +
          s.headers.map(escape).join(" | ") +
          " |\n| " +
          s.headers.map(() => "---").join(" | ") +
          " |\n" +
          s.rows
            .map((row) => "| " + row.map(escape).join(" | ") + " |")
            .join("\n"),
      )
      .join("\n\n")
  );
}

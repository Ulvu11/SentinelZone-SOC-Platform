import type { IncidentStatus, EndpointStatus } from "@/types";

const incidentColors: Record<IncidentStatus, string> = {
  open: "border-soc-danger text-soc-danger",
  investigating: "border-soc-warn text-soc-warn",
  contained: "border-soc-accent text-soc-accent",
  resolved: "border-soc-good text-soc-good",
};

const endpointColors: Record<EndpointStatus, string> = {
  healthy: "border-soc-good text-soc-good",
  warning: "border-soc-warn text-soc-warn",
  critical: "border-soc-danger text-soc-danger",
  offline: "border-soc-muted text-soc-muted",
};

export function IncidentStatusBadge({ status }: { status: IncidentStatus }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full border text-xs font-medium capitalize ${incidentColors[status]}`}
    >
      {status}
    </span>
  );
}

export function EndpointStatusBadge({ status }: { status: EndpointStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium capitalize ${endpointColors[status]}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          status === "healthy"
            ? "bg-soc-good"
            : status === "warning"
              ? "bg-soc-warn"
              : status === "critical"
                ? "bg-soc-danger"
                : "bg-soc-muted"
        }`}
      />
      {status}
    </span>
  );
}

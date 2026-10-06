export interface SocAlert {
  id: string; source: string; title: string; severity: string | null;
  eventTime: string | null; receivedAt: string | null;
  agentName: string | null; agentIp: string | null; sourceIp: string | null;
  destinationIp: string | null; ruleId: string | null;
}
export interface SocAlertSnapshot {
  status: "ok"; fetchedAt: string; limit: number; returnedRecords: number;
  rejectedRecords: number; duplicateRecords: number;
  newestEventAt: string | null; alerts: SocAlert[];
  overview?: {events_total:number;open_incidents_total:number};
  health?: {connectors:Record<string,{status:string;last_event_at:string|null}>;sensors:Record<string,{status:string;last_seen?:string|null}>};
  hasMore?:boolean;
}
export class InvalidAlertFeed extends Error {}
function text(value: unknown, maxLength = 240): string | null {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const result = String(value).trim();
  return result ? result.slice(0, maxLength) : null;
}
// Never interpret timezone-free received_at as the browser's local time.
export function parseEventTime(value: unknown): string | null {
  const raw = text(value);
  if (!raw) return null;
  let milliseconds: number;
  if (/^\d+(\.\d+)?$/.test(raw)) {
    const numeric = Number(raw);
    milliseconds = numeric >= 1e12 ? numeric : numeric * 1000;
  } else if (/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw)) {
    milliseconds = Date.parse(raw);
  } else return null;
  if (!Number.isFinite(milliseconds) || milliseconds < 0 || milliseconds > 8.64e15) return null;
  return new Date(Math.round(milliseconds)).toISOString();
}
export function sourceSeverity(alert: Pick<SocAlert, "source" | "severity">): string {
  if (alert.severity === null) return "Not provided";
  if (alert.source.toLowerCase() === "wazuh" && /^(?:[0-9]|1[0-5])$/.test(alert.severity)) return `Wazuh level ${alert.severity}`;
  return alert.severity;
}
export function normalizeAlertFeed(payload: unknown, fetchedAt = new Date().toISOString()): SocAlertSnapshot {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new InvalidAlertFeed();
  const feed = payload as Record<string, unknown>;
  if (!Array.isArray(feed.alerts) || feed.alerts.length > 50 || (feed.status !== undefined && feed.status !== "ok")) throw new InvalidAlertFeed();
  const seen = new Set<string>();
  let rejectedRecords = 0, duplicateRecords = 0;
  const alerts: SocAlert[] = [];
  for (const value of feed.alerts) {
    if (!value || typeof value !== "object" || Array.isArray(value)) { rejectedRecords++; continue; }
    const row = value as Record<string, unknown>;
    const id = text(row.id);
    if (!id) { rejectedRecords++; continue; }
    const source = text(row.source, 80) ?? "Unknown";
    const key = `${source}\u0000${id}`;
    if (seen.has(key)) { duplicateRecords++; continue; }
    seen.add(key);
    alerts.push({ id, source,
      title: text(row.alert_signature) ?? text(row.rule) ?? "Untitled alert",
      severity: text(row.severity, 80), eventTime: parseEventTime(row.event_time),
      receivedAt: text(row.received_at, 80), agentName: text(row.agent_name, 120),
      agentIp: text(row.agent_ip, 64), sourceIp: text(row.src_ip, 64),
      destinationIp: text(row.dest_ip, 64), ruleId: text(row.wazuh_rule_id, 80),
    });
  }
  if (feed.alerts.length && !alerts.length) throw new InvalidAlertFeed();
  const times = alerts.flatMap((alert) => alert.eventTime ? [alert.eventTime] : []);
  return { status: "ok", fetchedAt, limit: 50, returnedRecords: feed.alerts.length,
    rejectedRecords, duplicateRecords, newestEventAt: times.sort().at(-1) ?? null, alerts };
}
export function filterAlerts(alerts: SocAlert[], range: "1h" | "24h" | "7d", now: number, source = "", query = ""): SocAlert[] {
  const duration = (range === "1h" ? 1 : range === "7d" ? 168 : 24) * 3_600_000;
  const search = query.trim().toLowerCase();
  return alerts.filter((alert) => {
    const timestamp = alert.eventTime ? Date.parse(alert.eventTime) : NaN;
    return Number.isFinite(timestamp) && timestamp >= now - duration && timestamp <= now &&
      (!source || alert.source === source) && (!search ||
      [alert.id, alert.source, alert.title, alert.agentName, alert.agentIp, alert.sourceIp, alert.ruleId].some((value) => value?.toLowerCase().includes(search)));
  }).sort((a, b) => Date.parse(b.eventTime!) - Date.parse(a.eventTime!));
}

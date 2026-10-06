"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { RefreshCw, Database, Activity, Clock } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Panel } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { useTimeRange } from "@/components/time-range";
import { filterAlerts, sourceSeverity, type SocAlertSnapshot } from "@/lib/soc-alerts";

function utc(value: string | null): string {
  return value ? `${value.replace("T", " ").replace("Z", "")} UTC` : "N/A";
}
export function LiveAlertsWorkspace({ view }: { view: "overview" | "alerts" }) {
  const { range } = useTimeRange();
  const [snapshot, setSnapshot] = useState<SocAlertSnapshot | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [source, setSource] = useState("");
  const [query, setQuery] = useState("");
  const [lastSuccess, setLastSuccess] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<number | null>(null);
  const controller = useRef<AbortController | null>(null);
  const refresh = useCallback(async () => {
    controller.current?.abort();
    const active = new AbortController();
    controller.current = active;
    setBusy(true);
    const timeout = setTimeout(() => active.abort(), 12_000);
    try {
      const response = await fetch("/api/soc/alerts?range="+range, { cache: "no-store", signal: active.signal });
      const data = await response.json();
      if (!response.ok || data.status !== "ok" || !Array.isArray(data.alerts)) throw new Error(data.status ?? "unavailable");
      if (controller.current !== active) return;
      setSnapshot(data); setLastSuccess(data.fetchedAt); setFailure(null);
    } catch (error) {
      if (controller.current !== active) return;
      setSnapshot(null); setFailure(error instanceof Error ? error.message : "unavailable");
    } finally {
      clearTimeout(timeout);
      if (controller.current === active) { setCheckedAt(Date.now()); setBusy(false); }
    }
  }, [range]);
  useEffect(() => {
    const firstFetch = setTimeout(() => { void refresh(); }, 0);
    const timer = setInterval(() => { if (!document.hidden) void refresh(); }, 30_000);
    return () => { clearTimeout(firstFetch); clearInterval(timer); const active = controller.current; controller.current = null; active?.abort(); };
  }, [refresh]);

  const alerts = snapshot?.alerts ?? [];
  const sources = [...new Set(alerts.map((alert) => alert.source))].sort();
  const visible = filterAlerts(alerts, range, checkedAt ?? 0, source, query);
  const missingTimes = alerts.filter((alert) => !alert.eventTime).length;
  const futureTimes = alerts.filter((alert) => alert.eventTime && Date.parse(alert.eventTime) > (checkedAt ?? 0)).length;
  const severityCounts = new Map<string, number>();
  for (const alert of visible) {
    const label = `${alert.source} · ${sourceSeverity(alert)}`;
    severityCounts.set(label, (severityCounts.get(label) ?? 0) + 1);
  }
  return <div className="space-y-4">
    <PageHeader eyebrow="Security Operations Center" title={view === "overview" ? "Overview" : "Alerts"}
      description="Observed alerts from the SOC feed. All counts are limited to the returned records."
      actions={<button type="button" onClick={() => void refresh()} disabled={busy} className="control flex items-center gap-2 disabled:opacity-50"><RefreshCw size={15} className={busy ? "animate-spin" : ""} />{busy ? "Refreshing…" : "Refresh now"}</button>} />
    <div role="status" aria-live="polite" className="rounded-lg border border-soc-line bg-soc-surface p-4 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong className={failure ? "text-soc-warn" : "text-soc-accent"}>{busy ? "Checking alert feed…" : snapshot ? "Live feed · API reachable" : failure === "not_configured" ? "Alert source not configured" : "Alert source unavailable"}</strong>
        <span className="text-xs text-soc-muted">{lastSuccess ? `Last successful fetch: ${utc(lastSuccess)}` : "No successful fetch yet"}</span>
      </div>
      <p className="mt-2 text-soc-muted">{failure === "not_configured" ? "Start the local live dashboard connection to load SOC alerts." : failure === "invalid_response" ? "The source returned an unexpected response. No alert counts can be verified." : failure ? "The alert feed could not be read. Check SentinelZone backend and connector health, then refresh." : "Latest 500 records at most. This is a limited feed, not a complete history or a count of confirmed threats. Refreshes every 30 seconds while this page is visible."}</p>
      <p className="mt-1 text-xs text-soc-muted">REAL events only. Connector and sensor health are reported separately.</p>
    </div>
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Returned records" value={snapshot ? snapshot.returnedRecords : "N/A"} hint="Up to 500 · selected period" icon={<Database size={16} />} />
      <StatCard label="Matching records" value={snapshot ? visible.length : "N/A"} hint="Selected time range and filters" icon={<Activity size={16} />} />
      <StatCard label="Sources in returned feed" value={snapshot ? sources.length : "N/A"} hint="Source labels, not a sensor-health count" />
      <StatCard label="Newest event" value={utc(snapshot?.newestEventAt ?? null)} hint="Event time · separate from fetch time" icon={<Clock size={16} />} />
    </div>
    <div className="flex flex-wrap items-end gap-3">
      <label className="text-xs text-soc-muted">Source<select className="control mt-1 block min-w-40" value={source} onChange={(event) => setSource(event.target.value)}><option value="">All sources</option>{sources.map((item) => <option key={item} value={item}>{item}</option>)}{source && !sources.includes(source) && <option value={source}>{source} (not in this feed)</option>}</select></label>
      <label className="min-w-48 flex-1 text-xs text-soc-muted">Search returned records<input className="control mt-1 block w-full" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rule, host, source IP or record ID" /></label>
    </div>
    <p className="text-xs text-soc-muted">The selected time range is requested from SentinelZone PostgreSQL. The displayed records are a bounded page.</p>
    {snapshot && (missingTimes > 0 || futureTimes > 0 || snapshot.rejectedRecords > 0 || snapshot.duplicateRecords > 0) && <p role="status" className="rounded-lg border border-soc-line p-3 text-sm text-soc-warn">Data quality: {missingTimes} missing event times, {futureTimes} future event times, {snapshot.rejectedRecords} invalid records, {snapshot.duplicateRecords} duplicate IDs. Missing/future event times are excluded from time-filtered results.</p>}
    {view === "overview" && <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Panel title="Source severity" subtitle="Original source values in matching records">
        {snapshot && severityCounts.size > 0 ? <ul className="space-y-3">{[...severityCounts].sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true })).map(([label, count]) => <li key={label} className="flex justify-between gap-4 text-sm"><span>{label}</span><strong>{count}</strong></li>)}</ul> : <p className="text-sm text-soc-muted">{snapshot ? "No matching records in the returned feed." : "N/A · feed unavailable"}</p>}
        <p className="mt-4 text-xs text-soc-muted">Wazuh levels are preserved on their original 0–15 scale. Incident priority comes from the persisted backend correlation engine.</p>
      </Panel>
      <Panel title="Backend and sensor health" subtitle="Persisted telemetry and current connector state">
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between"><dt>Events in selected period</dt><dd>{snapshot?.overview?.events_total ?? "N/A"}</dd></div>
          <div className="flex justify-between"><dt>Open incidents in selected period</dt><dd>{snapshot?.overview?.open_incidents_total ?? "N/A"}</dd></div>
          {Object.entries(snapshot?.health?.connectors ?? {}).map(([name,s])=><div key={name} className="flex justify-between"><dt>{name}</dt><dd>{s.status}</dd></div>)}
          {Object.entries(snapshot?.health?.sensors ?? {}).map(([name,s])=><div key={"sensor-"+name} className="flex justify-between"><dt>{name} sensor</dt><dd>{s.status}</dd></div>)}
        </dl>
        <Link href="/hardware" className="link mt-4 inline-block text-xs">CryptoGuard hosts and resource telemetry →</Link>
      </Panel>
    </div>}
    <Panel title={view === "overview" ? "Recent matching alerts" : "Alert records"} subtitle="Expand a record to inspect its source fields. Records are not automatically incidents."
      action={view === "overview" ? <Link href="/alerts" className="text-xs text-soc-accent hover:underline">View all returned alerts</Link> : undefined}>
      {!snapshot ? <p className="py-6 text-center text-sm text-soc-muted">{busy ? "Loading source records…" : "No verified data is available."}</p> : visible.length === 0 ? <p className="py-6 text-center text-sm text-soc-muted">{alerts.length === 0 ? "The API returned an empty feed. Sensor health is not known." : "No records in this feed match the selected filters. Older history may exist."}</p> : <div className="space-y-2">{visible.slice(0, view === "overview" ? 8 : 500).map((alert) => <details key={`${alert.source}:${alert.id}`} className="rounded-lg border border-soc-line bg-soc-surface p-3">
        <summary className="cursor-pointer text-sm"><span className="font-medium break-words">{alert.title}</span><span className="ml-2 text-xs text-soc-muted">#{alert.id}</span><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-soc-muted"><span className="text-soc-accent">{alert.source} · {sourceSeverity(alert)}</span><span>Host: {alert.agentName ?? alert.agentIp ?? "N/A"}</span><span>{utc(alert.eventTime)}</span></div></summary>
        <dl className="mt-3 grid grid-cols-1 gap-3 border-t border-soc-line pt-3 text-xs sm:grid-cols-2 xl:grid-cols-3">{[["Source record ID", alert.id], ["Rule ID", alert.ruleId], ["Source IP", alert.sourceIp], ["Agent IP", alert.agentIp], ["Destination IP", alert.destinationIp], ["Received at (source text; timezone unverified)", alert.receivedAt]].map(([label, value]) => <div key={label}><dt className="text-soc-muted">{label}</dt><dd className="mt-1 break-all">{value ?? "N/A"}</dd></div>)}</dl>
      </details>)}</div>}
    </Panel>
  </div>;
}
